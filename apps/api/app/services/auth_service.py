from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
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

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
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
