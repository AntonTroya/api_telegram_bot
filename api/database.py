import sqlite3
from typing import List, Dict, Any, Tuple, Optional
from scraper.config import RAW_DATA_PATH

def get_db_connection():
    """Возвращает соединение с БД."""
    return sqlite3.connect(RAW_DATA_PATH)

def get_listings(
    min_price: Optional[float],
    max_price: Optional[float],
    rooms: Optional[int],
    min_area: Optional[float],
    max_area: Optional[float],
    address: Optional[str],
    is_active: bool,
    sort_by: str,
    order: str,
    page: int,
    limit: int
) -> Tuple[List[Dict], int]:
    """
    Возвращает список объявлений и общее количество (без пагинации).
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = []
    params = []

    if min_price is not None:
        conditions.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= ?")
        params.append(max_price)
    if rooms is not None:
        conditions.append("rooms = ?")
        params.append(rooms)
    if min_area is not None:
        conditions.append("area >= ?")
        params.append(min_area)
    if max_area is not None:
        conditions.append("area <= ?")
        params.append(max_area)
    if address:
        conditions.append("address LIKE ?")
        params.append(f"%{address}%")
    if is_active:
        conditions.append("is_active = 1")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Разрешённые поля для сортировки
    allowed_sort = {"price", "area", "first_seen"}
    sort_by = sort_by if sort_by in allowed_sort else "first_seen"
    order_sql = "DESC" if order.lower() == "desc" else "ASC"

    # Получаем общее количество
    count_sql = f"SELECT COUNT(*) as total FROM listings WHERE {where_clause}"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()["total"]

    # Пагинация
    offset = (page - 1) * limit
    sql = f"""
        SELECT id, title, price, address, area, rooms, floor, link, is_active
        FROM listings
        WHERE {where_clause}
        ORDER BY {sort_by} {order_sql}
        LIMIT ? OFFSET ?
    """
    cursor.execute(sql, params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows], total

def get_listing_by_id(listing_id: str) -> Optional[Dict]:
    """Возвращает одно объявление по ID."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_stats() -> Dict:
    """Возвращает агрегированную статистику по активным объявлениям."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total_active,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(area) as avg_area,
            COUNT(DISTINCT rooms) as distinct_room_counts
        FROM listings
        WHERE is_active = 1 AND price IS NOT NULL
    """)
    row = cursor.fetchone()
    conn.close()
    return {
        "total_active": row[0],
        "avg_price": round(row[1], 2) if row[1] else None,
        "min_price": row[2],
        "max_price": row[3],
        "avg_area": round(row[4], 2) if row[4] else None,
        "distinct_room_counts": row[5]
    }

