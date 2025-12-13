import asyncio
from time import monotonic

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.api import deps
from app.models.user import User


class RedisRateLimiter:
    """Sliding-window rate limiter stored in Redis for multi-instance deployments."""

    def __init__(self, calls: int, period_seconds: int, prefix: str = "rate"):
        self.calls = calls
        self.period = period_seconds
        self.prefix = prefix
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(deps.get_redis),
        current_user: User = Depends(deps.get_current_active_user),
    ) -> None:
        identifier = str(current_user.id) if current_user else request.client.host
        key = f"{self.prefix}:{identifier}:{request.url.path}"
        now = monotonic()
        window_start = now - self.period

        async with self._lock:
            await redis.zremrangebyscore(key, 0, window_start)
            current_count = await redis.zcard(key)

            if current_count >= self.calls:
                ttl = await redis.ttl(key)
                retry_after = ttl if ttl and ttl > 0 else int(self.period)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            pipeline = redis.pipeline()
            pipeline.zadd(key, {str(now): now})
            pipeline.expire(key, int(self.period))
            await pipeline.execute()
