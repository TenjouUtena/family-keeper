import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import get_redis
from app.core.security import ALGORITHM
from app.models import FamilyMember, User
from app.models.google_oauth import GoogleOAuthCredential

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
MEMBER_COLORS = ["#4F46E5", "#059669", "#DC2626", "#D97706", "#7C3AED", "#DB2777"]
EVENTS_CACHE_TTL = 300  # 5 minutes


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._fernet = Fernet(settings.FERNET_KEY.encode()) if settings.FERNET_KEY else None

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode()).decode()

    def build_auth_url(self, user_id: UUID) -> str:
        """Build Google OAuth consent URL with a JWT state parameter for CSRF."""
        state = jwt.encode(
            {
                "sub": str(user_id),
                "type": "google_oauth",
                "exp": datetime.now(UTC) + timedelta(minutes=10),
            },
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": CALENDAR_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URI}?{qs}"

    async def exchange_code(self, code: str, user_id: UUID) -> GoogleOAuthCredential:
        """Exchange authorization code for tokens, encrypt and store."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URI,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                logger.error("Google token exchange failed: %s", resp.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to exchange Google authorization code",
                )
            token_data = resp.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in)

        # Upsert
        result = await self.db.execute(
            select(GoogleOAuthCredential).where(GoogleOAuthCredential.user_id == user_id)
        )
        cred = result.scalar_one_or_none()

        if cred:
            cred.encrypted_access_token = self._encrypt(access_token)
            if refresh_token:
                cred.encrypted_refresh_token = self._encrypt(refresh_token)
            cred.token_expiry = token_expiry
            cred.scope = CALENDAR_SCOPE
        else:
            cred = GoogleOAuthCredential(
                user_id=user_id,
                encrypted_access_token=self._encrypt(access_token),
                encrypted_refresh_token=self._encrypt(refresh_token),
                token_expiry=token_expiry,
                scope=CALENDAR_SCOPE,
            )
            self.db.add(cred)

        await self.db.commit()
        await self.db.refresh(cred)
        return cred

    async def get_family_events(
        self, family_id: UUID, start: datetime, end: datetime
    ) -> dict:
        """Fetch events for all connected family members, merge and cache."""
        redis = await get_redis()
        cache_key = f"calendar:{family_id}:{start.isoformat()}:{end.isoformat()}"
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached if isinstance(cached, str) else cached.decode())
            return data

        # Get all family members + their OAuth creds
        result = await self.db.execute(
            select(FamilyMember, GoogleOAuthCredential, User)
            .join(User, FamilyMember.user_id == User.id)
            .outerjoin(GoogleOAuthCredential, User.id == GoogleOAuthCredential.user_id)
            .where(FamilyMember.family_id == family_id)
        )
        rows = result.all()

        total_members = len(rows)
        connected = [(member, cred, user) for member, cred, user in rows if cred is not None]
        connected_members = len(connected)

        # Parallel fetch
        tasks = [
            self._fetch_member_events(cred, start, end)
            for _, cred, _ in connected
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_events = []
        for i, events_or_error in enumerate(results):
            if isinstance(events_or_error, Exception):
                logger.warning("Failed to fetch events for member: %s", events_or_error)
                continue
            _, _, user = connected[i]
            color = MEMBER_COLORS[i % len(MEMBER_COLORS)]
            for event in events_or_error:
                event["member_name"] = user.username
                event["color"] = color
            all_events.extend(events_or_error)

        all_events.sort(key=lambda e: e.get("start", ""))

        response_data = {
            "events": all_events,
            "connected_members": connected_members,
            "total_members": total_members,
        }

        # Cache for 5 minutes
        await redis.setex(cache_key, EVENTS_CACHE_TTL, json.dumps(response_data))
        return response_data

    async def _refresh_token_if_needed(self, cred: GoogleOAuthCredential) -> str:
        """Return a valid access token, refreshing if expired."""
        if cred.token_expiry > datetime.now(UTC):
            return self._decrypt(cred.encrypted_access_token)

        refresh_token = self._decrypt(cred.encrypted_refresh_token)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GOOGLE_TOKEN_URI,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code != 200:
                logger.error("Google token refresh failed: %s", resp.text)
                raise RuntimeError("Failed to refresh Google token")
            token_data = resp.json()

        new_access = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)

        cred.encrypted_access_token = self._encrypt(new_access)
        cred.token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
        await self.db.commit()

        return new_access

    async def _fetch_member_events(
        self, cred: GoogleOAuthCredential, start: datetime, end: datetime
    ) -> list[dict]:
        """Fetch calendar events for one member via Google Calendar REST API."""
        access_token = await self._refresh_token_if_needed(cred)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "timeMin": start.isoformat(),
                    "timeMax": end.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": "100",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        events = []
        for item in data.get("items", []):
            start_val = item.get("start", {})
            end_val = item.get("end", {})
            events.append(
                {
                    "id": item["id"],
                    "title": item.get("summary", "(No title)"),
                    "start": start_val.get("dateTime") or start_val.get("date", ""),
                    "end": end_val.get("dateTime") or end_val.get("date"),
                    "all_day": "date" in start_val and "dateTime" not in start_val,
                }
            )
        return events
