import asyncio
import structlog
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.scraper import scrape_and_extract_listing
from app.services.listing_service import ListingService

# Configure logging at module level so it applies when arq loads the worker
setup_logging()
logger = structlog.get_logger()

async def startup(ctx):
    # Initialize DB Engine
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        future=True,
        echo=False,
    )
    ctx['sessionmaker'] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("worker.startup", status="initialized_db")

async def shutdown(ctx):
    # Retrieve engine from sessionmaker
    sessionmaker_instance = ctx.get('sessionmaker')
    if sessionmaker_instance:
        engine = sessionmaker_instance.kw['bind']
        await engine.dispose()
    logger.info("worker.shutdown", status="disposed_db")

async def process_listing(ctx, url: str):
    logger.info("worker.process_listing", url=url)
    
    # Scrape and Extract (async)
    result = await scrape_and_extract_listing(url)
    
    if result.get("error"):
        logger.error("worker.error", url=url, error=result["error"])
        return {"url": url, "error": result["error"]}

    # Save to DB
    session_maker = ctx['sessionmaker']
    async with session_maker() as session:
        await ListingService.create_or_update_listing(session, result)
    
    logger.info("worker.complete", url=url)
    return result

class WorkerSettings:
    functions = [process_listing]
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT
    )
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.WORKER_MAX_JOBS
    job_timeout = settings.WORKER_JOB_TIMEOUT
    keep_result = settings.WORKER_KEEP_RESULT
