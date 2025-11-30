from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.schemas.listing import Listing as ListingSchema, ListingScrapeRequest
from app.services.listing_service import ListingService

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
