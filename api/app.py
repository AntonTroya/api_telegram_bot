"""
FastAPI приложение для доступа к данным об объявлениях аренды квартир.
Документация: /docs или /redoc
"""
from fastapi import FastAPI, Query, HTTPException
from typing import Optional
from .models import PaginatedResponse, ListingDetail, StatsResponse
from .database import get_listings, get_listing_by_id, get_stats

app = FastAPI(
    title="BN.ru Rentals API",
    description="API для данных об аренде квартир в Санкт-Петербурге",
    version="1.0"
)

@app.get("/listings", response_model=PaginatedResponse)
async def listings_endpoint(
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
    rooms: Optional[int] = Query(None, ge=0, le=10, description="Кол-во комнат (0=студия)"),
    min_area: Optional[float] = Query(None, ge=0, description="Мин. площадь, м²"),
    max_area: Optional[float] = Query(None, ge=0, description="Макс. площадь, м²"),
    address: Optional[str] = Query(None, description="Часть адреса"),
    is_active: bool = Query(True, description="Только активные"),
    sort_by: str = Query("first_seen", pattern="^(price|area|first_seen)$", description="Сортировать по"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Порядок"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(20, ge=1, le=100, description="Записей на странице (max 100)")
):
    """
    Получить список объявлений с фильтрацией и пагинацией.
    """
    items, total = get_listings(
        min_price, max_price, rooms, min_area, max_area,
        address, is_active, sort_by, order, page, limit
    )
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total
    }

@app.get("/listings/{listing_id}", response_model=ListingDetail)
async def listing_detail(listing_id: str):
    """
    Получить детальную информацию об объявлении по ID.
    """
    listing = get_listing_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return listing

@app.get("/stats", response_model=StatsResponse)
async def stats():
    """
    Получить агрегированную статистику по активным объявлениям.
    """
    return get_stats()

# Для запуска напрямую: uvicorn api.app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


    