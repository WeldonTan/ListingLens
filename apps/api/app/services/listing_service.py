from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingUpdate

class ListingService:
    @staticmethod
    async def get_listings(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Listing]:
        result = await db.execute(select(Listing).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def get_listing(db: AsyncSession, id: int) -> Optional[Listing]:
        return await db.get(Listing, id)
    
    @staticmethod
    async def get_listings_by_ids(db: AsyncSession, ids: List[int]) -> List[Listing]:
        result = await db.execute(select(Listing).filter(Listing.id.in_(ids)))
        return result.scalars().all()

    @staticmethod
    async def create_or_update_listing(db: AsyncSession, data: dict) -> Listing:
        # Check if listing exists by URL
        result = await db.execute(select(Listing).filter(Listing.url == data['url']))
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
            "tenure": data.get("tenure"),
            "furnishing": data.get("furnishing"),
            "completion_year": data.get("completion_year"),
        }

        if existing_listing:
            for key, value in listing_data.items():
                setattr(existing_listing, key, value)
            listing = existing_listing
        else:
            listing = Listing(**listing_data)
            db.add(listing)
        
        await db.commit()
        await db.refresh(listing)
        return listing

    @staticmethod
    async def delete_listing(db: AsyncSession, id: int) -> bool:
        listing = await db.get(Listing, id)
        if not listing:
            return False
        await db.delete(listing)
        await db.commit()
        return True

    @staticmethod
    async def delete_all_listings(db: AsyncSession) -> None:
        await db.execute(delete(Listing))
        await db.commit()
