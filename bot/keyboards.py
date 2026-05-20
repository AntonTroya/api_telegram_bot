from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_pagination_keyboard(page: int, total_pages: int, callback_prefix: str = "page"):
    """Создаёт клавиатуру для переключения страниц."""
    keyboard = []
    if total_pages > 1:
        row = []
        if page > 1:
            row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"{callback_prefix}_{page-1}"))
        if page < total_pages:
            row.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"{callback_prefix}_{page+1}"))
        if row:
            keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])
    return InlineKeyboardMarkup(keyboard)

def get_main_menu():
    """Главное меню."""
    keyboard = [
        [InlineKeyboardButton("🔎 Найти квартиры", callback_data="search")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_filter_buttons():
    """Быстрые фильтры (например, по комнатам)."""
    keyboard = [
        [InlineKeyboardButton("Студии", callback_data="filter_rooms_0")],
        [InlineKeyboardButton("1-комнатные", callback_data="filter_rooms_1")],
        [InlineKeyboardButton("2-комнатные", callback_data="filter_rooms_2")],
        [InlineKeyboardButton("3+ комнат", callback_data="filter_rooms_3")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

