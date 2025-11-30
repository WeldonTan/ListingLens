from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import engine
from app.db.base import Base

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (for simplicity in this task, ideally use Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Arq Redis Pool
    app.state.arq_pool = await create_pool(
        RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    )
    
    yield
    
    # Close Arq Redis Pool
    await app.state.arq_pool.close()

app = FastAPI(
    title=settings.PROJECT_NAME, 
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
