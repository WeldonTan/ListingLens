from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, DateTime
from sqlalchemy.sql import func
import datetime
from app.db.base_class import Base

class Listing(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    
    listing_title: Mapped[Optional[str]] = mapped_column(String)
    project_name: Mapped[Optional[str]] = mapped_column(String)
    area: Mapped[Optional[str]] = mapped_column(String)
    state: Mapped[Optional[str]] = mapped_column(String)
    price: Mapped[Optional[float]] = mapped_column(Float)
    sq_ft: Mapped[Optional[float]] = mapped_column(Float)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer)
    property_type: Mapped[Optional[str]] = mapped_column(String)
    carpark: Mapped[Optional[int]] = mapped_column(Integer)
    floor_range: Mapped[Optional[str]] = mapped_column(String)
    phone_number: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    tenure: Mapped[Optional[str]] = mapped_column(String)
    furnishing: Mapped[Optional[str]] = mapped_column(String)
    completion_year: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
