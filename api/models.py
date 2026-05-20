from pydantic import BaseModel
from typing import Optional, List

class ListingBase(BaseModel):
    id: str
    title: Optional[str] = None
    price: Optional[float] = None
    address: Optional[str] = None
    area: Optional[float] = None
    rooms: Optional[int] = None
    floor: Optional[str] = None
    link: Optional[str] = None
    is_active: int

class ListingDetail(ListingBase):
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

class ListingResponse(ListingBase):
    pass

class PaginatedResponse(BaseModel):
    items: List[ListingResponse]
    page: int
    limit: int
    total: int

class StatsResponse(BaseModel):
    total_active: int
    avg_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    avg_area: Optional[float] = None
    distinct_room_counts: int


    