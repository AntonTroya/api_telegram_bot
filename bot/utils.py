import requests
from bot.config import API_BASE_URL, DEFAULT_LIMIT, MAX_LIMIT

def get_listings(params: dict) -> dict:
    """
    Отправка сетевого запроса к API, перевод параметров page во внутренние
    переменные лимита и смещения
    """
    api_params = params.copy()
    page = api_params.pop("page", 1)
    limit = api_params.get("limit", DEFAULT_LIMIT)
    
    limit = min(limit, MAX_LIMIT)
    api_params["limit"] = limit
    api_params["offset"] = (page - 1) * limit

    try:
        resp = requests.get(f"{API_BASE_URL}/listings", params=api_params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_stats() -> dict:
    """Запрос агрегированных показателей на сервере API"""
    try:
        resp = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def format_listing(listing: dict) -> str:
    """Форматирование карточки одного объекта недвижимости для вывода"""
    lines = [
        f"🏠 *{listing.get('title', 'Без названия')}*",
        f"💰 Цена: {listing.get('price', 'не указана')} руб.",
        f"📍 Адрес: {listing.get('address', 'не указан')}",
        f"📐 Площадь: {listing.get('area', '?')} м²",
        f"🚪 Комнат: {listing.get('rooms', '?')}",
        f"📊 Этаж: {listing.get('floor', '?')}",
        f"🔗 [Открыть на сайте BN.ru]({listing.get('link', '')})"
    ]
    return "\n".join(lines)

def format_stats(stats: dict) -> str:
    """Подготовка текстовой сводки общих показателей по рынку"""
    return (
        f"📊 *Статистика по активным объявлениям*\n\n"
        f"• Всего предложений: {stats.get('total_active', 0)}\n"
        f"• Средняя стоимость: {stats.get('avg_price', 0):,.0f} руб.\n"
        f"• Минимальная цена: {stats.get('min_price', 0):,.0f} руб.\n"
        f"• Максимальная цена: {stats.get('max_price', 0):,.0f} руб.\n"
        f"• Средняя площадь: {stats.get('avg_area', 0):.1f} м²\n"
        f"• Разнообразие планировок: {stats.get('distinct_room_counts', 0)}"
    )
