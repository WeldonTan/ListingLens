from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
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

docs_url = "/docs" if settings.ENVIRONMENT != "production" else None
redoc_url = "/redoc" if settings.ENVIRONMENT != "production" else None

if settings.BACKEND_CORS_ALLOW_CREDENTIALS and "*" in settings.BACKEND_CORS_ORIGINS:
    raise ValueError("CORS allow_origins cannot be '*' when credentials are allowed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if docs_url else None,
    docs_url=docs_url,
    redoc_url=redoc_url,
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=settings.BACKEND_CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
