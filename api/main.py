"""
Интерфейс API для работы с БД BN.ru
"""
import sqlite3
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Path as PathParam
from pydantic import BaseModel

app = FastAPI(
    title="BN.ru API",
    description="API для доступа к базе данных аренды квартир Санкт-Петербурга",
    version="1.1.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "raw" / "spb_rentals.db"


class ListingSchema(BaseModel):
    id: str
    title: Optional[str] = None
    price: Optional[float] = None
    address: Optional[str] = None
    area: Optional[float] = None
    rooms: Optional[int] = None
    floor: Optional[str] = None
    link: Optional[str] = None
    district: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    is_active: int


class PaginatedListingsSchema(BaseModel):
    items: List[ListingSchema]
    total: int
    page: int
    limit: int


class GeneralStatsSchema(BaseModel):
    total_active: int
    avg_price: float
    min_price: float
    max_price: float
    avg_area: float
    distinct_room_counts: int


def get_db_connection():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500, 
            detail="База данных отсутствует. Сначала запустите скрапер."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/listings", response_model=PaginatedListingsSchema, summary="Получить список объявлений")
def get_listings(
    limit: int = Query(5, ge=1, le=50),
    offset: int = Query(0, ge=0),
    district: Optional[str] = Query(None),
    rooms: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_area: Optional[float] = Query(None),
    max_area: Optional[float] = Query(None),
    sort_by: str = Query("price", pattern="^(price|area|first_seen)$"),
    order: str = Query("asc", pattern="^(asc|desc)$")
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Сборка условий
    where_clauses = ["1=1"]
    params = []

    if district:
        where_clauses.append("district LIKE ?")
        params.append(f"%{district}%")
    if rooms is not None:
        where_clauses.append("rooms = ?")
        params.append(rooms)
    if min_price is not None:
        where_clauses.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        where_clauses.append("price <= ?")
        params.append(max_price)
    if min_area is not None:
        where_clauses.append("area >= ?")
        params.append(min_area)
    if max_area is not None:
        where_clauses.append("area <= ?")
        params.append(max_area)

    where_str = " AND ".join(where_clauses)

    # Подсчет общего количества записей под условия фильтра
    count_query = f"SELECT COUNT(*) FROM listings WHERE {where_str}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]

    # Сборка и исполнение основного запроса
    main_query = f"SELECT * FROM listings WHERE {where_str} ORDER BY {sort_by} {order.upper()} LIMIT ? OFFSET ?"
    query_params = params + [limit, offset]
    cursor.execute(main_query, query_params)
    rows = cursor.fetchall()
    conn.close()

    page_num = (offset // limit) + 1

    return {
        "items": [dict(row) for row in rows],
        "total": total_count,
        "page": page_num,
        "limit": limit
    }


@app.get("/stats", response_model=GeneralStatsSchema, summary="Общая аналитика активной базы объявлений")
def get_general_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                COUNT(*),
                AVG(price),
                MIN(price),
                MAX(price),
                AVG(area),
                COUNT(DISTINCT rooms)
            FROM listings 
            WHERE is_active = 1 AND price IS NOT NULL AND price > 0
        """)
        row = cursor.fetchone()
        return {
            "total_active": row[0] or 0,
            "avg_price": row[1] or 0.0,
            "min_price": row[2] or 0.0,
            "max_price": row[3] or 0.0,
            "avg_area": row[4] or 0.0,
            "distinct_room_counts": row[5] or 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
        