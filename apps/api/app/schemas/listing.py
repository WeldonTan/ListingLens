from typing import Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class ListingBase(BaseModel):
    url: str
    listing_title: Optional[str] = None
    project_name: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    price: Optional[float] = None
    sq_ft: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    carpark: Optional[int] = None
    floor_range: Optional[str] = None
    phone_number: Optional[str] = None
    description: Optional[str] = None
    tenure: Optional[str] = None
    furnishing: Optional[str] = None
    completion_year: Optional[int] = None

class ListingCreate(ListingBase):
    pass

class ListingUpdate(ListingBase):
    pass

class ListingInDBBase(ListingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Listing(ListingInDBBase):
    pass

class ListingScrapeRequest(BaseModel):
    urls: list[str]

class ListingGenerateRequest(BaseModel):
    listing_ids: list[int]
    instruction: str
