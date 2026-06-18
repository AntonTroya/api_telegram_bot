from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔎 Быстрый поиск", callback_data="search")],
        [InlineKeyboardButton("📊 Общая статистика", callback_data="stats")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_filter_buttons() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Студии", callback_data="filter_rooms_0")],
        [InlineKeyboardButton("1-комнатные", callback_data="filter_rooms_1")],
        [InlineKeyboardButton("2-комнатные", callback_data="filter_rooms_2")],
        [InlineKeyboardButton("3+ комнат", callback_data="filter_rooms_3")],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
