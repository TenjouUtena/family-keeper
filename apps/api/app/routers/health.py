from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    db_ok = False
    redis_ok = False

    # Check database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # Check Redis
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        redis_ok = True
        await redis_client.aclose()
    except Exception:
        pass

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}
