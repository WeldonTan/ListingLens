from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.db.session import get_db
from app.models.listing import Listing
from app.schemas.listing import Listing as ListingSchema, ListingScrapeRequest
from app.worker import process_listing

router = APIRouter()

@router.get("/", response_model=List[ListingSchema])
async def read_listings(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    # current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve listings.
    """
    result = await db.execute(select(Listing).offset(skip).limit(limit))
    listings = result.scalars().all()
    return listings

@router.post("/scrape", status_code=202)
async def scrape_listings(
    request: ListingScrapeRequest,
    # current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Trigger scraping for a list of URLs.
    """
    task_ids = []
    for url in request.urls:
        task = process_listing.delay(url)
        task_ids.append(str(task.id))
    
    return {"message": "Scraping started", "task_ids": task_ids}

@router.get("/{id}", response_model=ListingSchema)
async def read_listing(
    id: int,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get listing by ID.
    """
    listing = await db.get(Listing, id)
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
    listing = await db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    await db.delete(listing)
    await db.commit()
    return {"message": "Listing deleted successfully"}

@router.delete("/", status_code=200)
async def delete_all_listings(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Delete all listings.
    """
    # Use delete statement for bulk delete
    from sqlalchemy import delete
    await db.execute(delete(Listing))
    await db.commit()
    return {"message": "All listings deleted successfully"}
