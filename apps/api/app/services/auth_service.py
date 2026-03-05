import logging
import re
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, status
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_CERTS_URI = "https://www.googleapis.com/oauth2/v3/certs"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> tuple[User, TokenResponse]:
        email = data.email.lower()

        # Check email uniqueness
        existing = await self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        # Check username uniqueness
        existing = await self.db.scalar(select(User).where(User.username == data.username))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )

        user = User(
            email=email,
            username=data.username,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()

        tokens = await self._create_tokens(user)
        await self.db.commit()
        return user, tokens

    async def login(self, data: LoginRequest) -> tuple[User, TokenResponse]:
        email = data.email.lower()
        user = await self.db.scalar(select(User).where(User.email == email))

        if not user or not user.password_hash:
            if user and not user.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This account uses Google sign-in. Please sign in with Google.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

        tokens = await self._create_tokens(user)
        await self.db.commit()
        return user, tokens

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(raw_refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        token_hash_value = hash_token(raw_refresh_token)
        stored_token = await self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash_value)
        )

        if not stored_token or stored_token.revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

        if stored_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        # Revoke old token
        stored_token.revoked = True

        # Load user
        user = await self.db.get(User, stored_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        tokens = await self._create_tokens(user)
        await self.db.commit()
        return tokens

    @staticmethod
    async def logout(access_token: str) -> None:
        try:
            payload = decode_token(access_token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(UTC).timestamp()), 0)
        if jti and ttl > 0:
            await blacklist_token(jti, ttl)

    @staticmethod
    def build_google_auth_url() -> str:
        """Build Google OAuth consent URL for authentication."""
        from urllib.parse import urlencode

        from app.core.security import ALGORITHM

        state = jose_jwt.encode(
            {
                "type": "google_auth",
                "exp": datetime.now(UTC) + timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_AUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    async def google_auth(self, code: str) -> tuple[User, TokenResponse]:
        """Authenticate via Google OAuth authorization code."""
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URI,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_AUTH_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                logger.error("Google token exchange failed: %s", resp.text)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to authenticate with Google",
                )
            token_data = resp.json()

        # Decode and verify ID token
        id_token = token_data.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from Google",
            )

        # Fetch Google's public keys and verify
        async with httpx.AsyncClient() as client:
            certs_resp = await client.get(GOOGLE_CERTS_URI)
            google_keys = certs_resp.json()

        try:
            claims = jose_jwt.decode(
                id_token,
                google_keys,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID,
                options={"verify_at_hash": False},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google ID token",
            )

        google_sub = claims["sub"]
        email = claims.get("email", "").lower()
        name = claims.get("name", "")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account has no email",
            )

        # 1. Look up by google_sub
        user = await self.db.scalar(select(User).where(User.google_sub == google_sub))

        if not user:
            # 2. Look up by email
            user = await self.db.scalar(select(User).where(User.email == email))
            if user:
                # Link Google to existing account
                user.google_sub = google_sub
            else:
                # 3. Create new user
                username = self._derive_username(email, name)
                # Ensure username uniqueness
                base_username = username
                counter = 1
                while await self.db.scalar(select(User).where(User.username == username)):
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(
                    email=email,
                    username=username,
                    password_hash=None,
                    auth_provider="google",
                    google_sub=google_sub,
                )
                self.db.add(user)
                await self.db.flush()

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled"
            )

        tokens = await self._create_tokens(user)
        await self.db.commit()
        return user, tokens

    @staticmethod
    def _derive_username(email: str, name: str) -> str:
        """Derive a username from Google profile info."""
        if name:
            # Convert "John Doe" to "john_doe"
            username = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip()).lower()
            username = re.sub(r"_+", "_", username).strip("_")
            if 3 <= len(username) <= 50:
                return username
        # Fall back to email local part
        local = email.split("@")[0]
        username = re.sub(r"[^a-zA-Z0-9_-]", "_", local).lower()
        username = re.sub(r"_+", "_", username).strip("_")
        if len(username) < 3:
            username = username + "_user"
        return username[:50]

    async def _create_tokens(self, user: User) -> TokenResponse:
        access_token, _ = create_access_token(user.id)
        raw_refresh, refresh_hash = create_refresh_token(user.id)

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(db_token)

        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)
