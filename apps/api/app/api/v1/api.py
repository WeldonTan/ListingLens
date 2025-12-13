from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.v1.endpoints import listings, auth
from app.api import deps
from app.db.session import get_db

api_router = APIRouter()
api_router.include_router(auth.router, tags=["login"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}


@api_router.get("/health/full")
async def health_check_full(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(deps.get_redis),
):
    """Comprehensive health check that verifies DB and Redis connectivity."""

    await db.execute(text("SELECT 1"))
    await redis.ping()

    return {"status": "ok", "database": "ok", "redis": "ok"}
