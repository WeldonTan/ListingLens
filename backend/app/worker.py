import asyncio
from celery import Celery
from app.core.config import settings
from app.services.scraper import scrape_url
from app.services.gemini import extract_property_details
from app.models.listing import Listing
from sqlalchemy.future import select
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

async def save_listing_to_db(data: dict):
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
            # Check if listing exists
            result = await session.execute(select(Listing).filter(Listing.url == data['url']))
            existing_listing = result.scalars().first()
            
            listing_data = {
                "url": data.get("url"),
                "listing_title": data.get("listing_title"),
                "project_name": data.get("project_name"),
                "area": data.get("area"),
                "state": data.get("state"),
                "price": data.get("price"),
                "sq_ft": data.get("sq_ft"),
                "bedrooms": data.get("bedrooms"),
                "bathrooms": data.get("bathrooms"),
                "property_type": data.get("property_type"),
                "carpark": data.get("carpark"),
                "floor_range": data.get("floor_range"),
                "phone_number": data.get("phone_number"),
                "description": data.get("description"),
            }

            if existing_listing:
                for key, value in listing_data.items():
                    setattr(existing_listing, key, value)
            else:
                new_listing = Listing(**listing_data)
                session.add(new_listing)
            
            await session.commit()
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
    run_async(save_listing_to_db(gemini_result))
    
    return gemini_result
