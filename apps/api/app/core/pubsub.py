import json
import logging
from uuid import UUID

from redis.asyncio import Redis

from app.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def publish_list_event(list_id: UUID, event: str, data: dict | None = None) -> None:
    """Publish a list mutation event to Redis pub/sub.

    Uses the shared Redis client (PUBLISH does not block).
    Fire-and-forget — errors are logged but never raised.
    """
    try:
        redis = await get_redis()
        payload = json.dumps({"event": event, "list_id": str(list_id), **(data or {})})
        await redis.publish(f"list:{list_id}", payload)
    except Exception:
        logger.warning("Failed to publish list event %s for %s", event, list_id, exc_info=True)


async def subscribe_list(list_id: UUID) -> tuple:
    """Create a NEW Redis connection and subscribe to a list channel.

    Returns (pubsub, redis_conn). Caller is responsible for cleanup:
        await pubsub.unsubscribe(...)
        await pubsub.aclose()
        await redis_conn.aclose()
    """
    redis_conn = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(f"list:{list_id}")
    return pubsub, redis_conn
