import requests
from .config import API_BASE_URL, DEFAULT_LIMIT, MAX_LIMIT

def get_listings(params: dict) -> dict:
    """
    params: dict с параметрами фильтрации:
        min_price, max_price, rooms, min_area, max_area,
        address, is_active, sort_by, order, page, limit
    Возвращает ответ API (items, total, page, limit)
    """
    # Ограничиваем limit
    if "limit" in params:
        params["limit"] = min(params["limit"], MAX_LIMIT)
    else:
        params["limit"] = DEFAULT_LIMIT
    try:
        resp = requests.get(f"{API_BASE_URL}/listings", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_stats() -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def format_listing(listing: dict) -> str:
    """Форматирует одно объявление для вывода в Telegram."""
    lines = [
        f"🏠 {listing.get('title', 'Без названия')}",
        f"💰 Цена: {listing.get('price', 'не указана')} руб.",
        f"📍 {listing.get('address', 'адрес не указан')}",
        f"📐 Площадь: {listing.get('area', '?')} м²",
        f"🚪 Комнат: {listing.get('rooms', '?')}",
        f"📊 Этаж: {listing.get('floor', '?')}",
        f"🔗 {listing.get('link', '')}"
    ]
    return "\n".join(lines)

def format_stats(stats: dict) -> str:
    return (
        f"📊 *Статистика по активным объявлениям*\n\n"
        f"Всего: {stats.get('total_active', 0)}\n"
        f"Средняя цена: {stats.get('avg_price', 0):,.0f} руб.\n"
        f"Мин. цена: {stats.get('min_price', 0):,.0f} руб.\n"
        f"Макс. цена: {stats.get('max_price', 0):,.0f} руб.\n"
        f"Средняя площадь: {stats.get('avg_area', 0):.1f} м²\n"
        f"Количество разных кол-в комнат: {stats.get('distinct_room_counts', 0)}"
    )

