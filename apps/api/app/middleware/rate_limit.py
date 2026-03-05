import time

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis

RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10


async def rate_limit_auth(request: Request) -> None:
    """Sliding window rate limiter: 10 requests per minute per IP on auth endpoints."""
    redis = await get_redis()
    ip = request.client.host if request.client else "unknown"
    key = f"ratelimit:auth:{ip}"
    now = time.time()

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, RATE_LIMIT_WINDOW)
    results = await pipe.execute()

    count = results[2]
    if count > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests"
        )
