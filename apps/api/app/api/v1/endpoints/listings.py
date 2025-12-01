import asyncio
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from arq.jobs import Job
from app.schemas.listing import Listing as ListingSchema, ListingScrapeRequest, ListingGenerateRequest
from app.services.listing_service import ListingService
from app.services.scraper import generate_listing_content

router = APIRouter()

@router.get("/", response_model=List[ListingSchema])
async def read_listings(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve listings.
    """
    return await ListingService.get_listings(db, skip, limit)

@router.post("/scrape", status_code=202)
async def scrape_listings(
    request: Request,
    scrape_req: ListingScrapeRequest,
) -> Any:
    """
    Trigger scraping for a list of URLs.
    """
    task_ids = []
    pool = request.app.state.arq_pool
    
    for url in scrape_req.urls:
        job = await pool.enqueue_job('process_listing', url)
        if job:
            task_ids.append(job.job_id)
    
    return {"message": "Scraping started", "task_ids": task_ids}

@router.post("/scrape/status")
async def check_scrape_status(
    request: Request,
    task_ids: List[str],
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
            
    return statuses

@router.post("/scrape/cancel")
async def cancel_scrape_tasks(
    request: Request,
    task_ids: List[str],
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
            
    return {"message": "Cancellation requested"}

@router.post("/scrape/purge")
async def purge_queue(
    request: Request,
) -> Any:
    """
    Purge the scraping queue.
    """
    pool = request.app.state.arq_pool
    # Flush DB to remove all queued jobs and job results
    # This is safe because Redis is dedicated to this app
    await pool.execute_command("FLUSHDB")
    return {"message": "Queue purged"}

@router.get("/{id}", response_model=ListingSchema)
async def read_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get listing by ID.
    """
    listing = await ListingService.get_listing(db, id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

@router.delete("/{id}", status_code=200)
async def delete_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete listing by ID.
    """
    success = await ListingService.delete_listing(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"message": "Listing deleted successfully"}

@router.delete("/", status_code=200)
async def delete_all_listings(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete all listings.
    """
    await ListingService.delete_all_listings(db)
    return {"message": "All listings deleted successfully"}

@router.post("/generate-copy", status_code=200)
async def generate_copy(
    req: ListingGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Generate copy for a list of listings.
    """
    listings = await ListingService.get_listings_by_ids(db, req.listing_ids)
    if not listings:
        raise HTTPException(status_code=404, detail="No listings found for the given IDs")

    async def generate_for_listing(listing):
        listing_data = jsonable_encoder(ListingSchema.from_orm(listing))
        generated_text = await generate_listing_content(listing_data, req.instruction)
        return {"id": listing.id, "generated_text": generated_text}

    tasks = [generate_for_listing(listing) for listing in listings]
    results = await asyncio.gather(*tasks)
    
    return results
