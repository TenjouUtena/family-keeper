import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.redis import get_redis

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Create an access token. Returns (token, jti)."""
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Create a refresh token. Returns (raw_token, token_hash)."""
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    raw_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def hash_token(raw_token: str) -> str:
    """SHA-256 hash of a raw token for DB storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add an access token JTI to the Redis blacklist."""
    redis = await get_redis()
    await redis.setex(f"blacklist:{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Check if an access token JTI is blacklisted."""
    redis = await get_redis()
    return await redis.exists(f"blacklist:{jti}") > 0


__all__ = [
    "ALGORITHM",
    "JWTError",
    "blacklist_token",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "hash_token",
    "is_token_blacklisted",
    "verify_password",
]
