import asyncio
from typing import Any, List
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from arq.jobs import Job
from app.core.config import settings
from app.core.rate_limiter import RedisRateLimiter
from app.models.user import User
from app.schemas.listing import Listing as ListingSchema, ListingScrapeRequest, ListingGenerateRequest
from app.services.listing_service import ListingService
from app.services.scraper import generate_listing_content

logger = structlog.get_logger(__name__)

router = APIRouter(dependencies=[Depends(deps.get_current_active_user)])
submission_rate_limiter = RedisRateLimiter(
    calls=settings.RATE_LIMIT_SUBMISSION_CALLS,
    period_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    prefix="rate:listings:submit",
)
status_rate_limiter = RedisRateLimiter(
    calls=settings.RATE_LIMIT_STATUS_CALLS,
    period_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    prefix="rate:listings:status",
)

@router.get("/", response_model=List[ListingSchema])
async def read_listings(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve listings.
    """
    logger.info("listings_read", user_id=current_user.id, skip=skip, limit=limit)
    return await ListingService.get_listings(db, skip, limit)

@router.post("/scrape", status_code=202)
async def scrape_listings(
    request: Request,
    scrape_req: ListingScrapeRequest,
    current_user: User = Depends(deps.get_current_active_user),
    _: None = Depends(submission_rate_limiter),
) -> Any:
    """
    Trigger scraping for a list of URLs.
    """
    normalized_urls = list(dict.fromkeys([str(url) for url in scrape_req.urls]))

    if not normalized_urls:
        raise HTTPException(status_code=400, detail="At least one URL is required")

    if len(normalized_urls) > settings.MAX_SCRAPE_URLS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {settings.MAX_SCRAPE_URLS_PER_REQUEST} URLs are allowed per request.",
        )

    task_ids = []
    pool = request.app.state.arq_pool

    for url in normalized_urls:
        job = await pool.enqueue_job("process_listing", url)
        if job:
            task_ids.append(job.job_id)

    logger.info(
        "scrape_enqueued",
        user_id=current_user.id,
        task_count=len(task_ids),
        urls=len(normalized_urls),
    )
    return {"message": "Scraping started", "task_ids": task_ids}

@router.post("/scrape/status")
async def check_scrape_status(
    request: Request,
    task_ids: List[str],
    _: None = Depends(status_rate_limiter),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Check status of scraping tasks.
    """
    pool = request.app.state.arq_pool
    statuses = {}
    
    for task_id in task_ids:
        try:
            job = Job(task_id, pool)
            status = await job.status()
            result = None
            if status == "complete":
                try:
                    result = await job.result()
                except Exception:
                    pass
            
            statuses[task_id] = {"status": status, "result": result}
        except Exception:
            statuses[task_id] = {"status": "unknown", "result": None}
            
    logger.info("scrape_status_checked", user_id=current_user.id, task_count=len(task_ids))
    return statuses

@router.post("/scrape/cancel")
async def cancel_scrape_tasks(
    request: Request,
    task_ids: List[str],
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Cancel scraping tasks.
    """
    pool = request.app.state.arq_pool
    
    for task_id in task_ids:
        try:
            job = Job(task_id, pool)
            await job.abort(timeout=0.1)
        except Exception:
            pass
            
    logger.info("scrape_cancellation_requested", user_id=current_user.id, task_count=len(task_ids))
    return {"message": "Cancellation requested"}

@router.post("/scrape/purge")
async def purge_queue(
    request: Request,
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Purge the scraping queue.
    """
    pool = request.app.state.arq_pool
    # Flush DB to remove all queued jobs and job results
    # This is safe because Redis is dedicated to this app
    await pool.execute_command("FLUSHDB")
    logger.info("queue_purged", user_id=current_user.id)
    return {"message": "Queue purged"}

@router.get("/{id}", response_model=ListingSchema)
async def read_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get listing by ID.
    """
    listing = await ListingService.get_listing(db, id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    logger.info("listing_read", user_id=current_user.id, listing_id=id)
    return listing

@router.delete("/{id}", status_code=200)
async def delete_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete listing by ID.
    """
    success = await ListingService.delete_listing(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    logger.info("listing_deleted", user_id=current_user.id, listing_id=id)
    return {"message": "Listing deleted successfully"}

@router.delete("/", status_code=200)
async def delete_all_listings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Delete all listings.
    """
    await ListingService.delete_all_listings(db)
    logger.warning("all_listings_deleted", user_id=current_user.id)
    return {"message": "All listings deleted successfully"}

@router.post("/generate-copy", status_code=200)
async def generate_copy(
    req: ListingGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
    _: None = Depends(submission_rate_limiter),
) -> Any:
    """
    Generate copy for a list of listings.
    """
    normalized_ids = list(dict.fromkeys(req.listing_ids))

    if not normalized_ids:
        raise HTTPException(status_code=400, detail="At least one listing id is required")

    if len(normalized_ids) > settings.MAX_GENERATE_IDS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"A maximum of {settings.MAX_GENERATE_IDS_PER_REQUEST} listing ids are allowed per request.",
        )

    listings = await ListingService.get_listings_by_ids(db, normalized_ids)
    if not listings:
        raise HTTPException(status_code=404, detail="No listings found for the given IDs")

    async def generate_for_listing(listing):
        listing_data = jsonable_encoder(ListingSchema.from_orm(listing))
        generated_text = await generate_listing_content(listing_data, req.instruction)
        return {"id": listing.id, "generated_text": generated_text}

    tasks = [generate_for_listing(listing) for listing in listings]
    results = await asyncio.gather(*tasks)

    logger.info(
        "copy_generated",
        user_id=current_user.id,
        listing_count=len(results),
        instruction_length=len(req.instruction or ""),
    )

    return results
