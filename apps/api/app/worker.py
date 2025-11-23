import asyncio
from celery import Celery
from app.core.config import settings
from app.services.scraper import scrape_url
from app.services.gemini import extract_property_details
from app.services.listing_service import ListingService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
)

# celery_app.conf.task_routes = {
#     "app.worker.process_listing": "main-queue",
# }

async def save_listing(data: dict):
    # Create a dedicated engine/session for this task to avoid loop mismatch in Celery
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        future=True,
        echo=False,
    )
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            await ListingService.create_or_update_listing(session, data)
    finally:
        await engine.dispose()

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(acks_late=True)
def process_listing(url: str):
    # 1. Scrape
    scrape_result = scrape_url(url)
    if scrape_result.get("error"):
        # Log error
        return {"url": url, "error": scrape_result["error"]}
    
    html_content = scrape_result.get("html")
    if not html_content:
         return {"url": url, "error": "No HTML content"}

    # 2. Gemini Extraction
    # We need to run async gemini call in sync celery task
    gemini_result = run_async(extract_property_details(html_content, url))
    
    if gemini_result.get("error"):
         return gemini_result

    # 3. Save to DB
    run_async(save_listing(gemini_result))
    
    return gemini_result
