import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .utils import get_listings, get_stats, format_listing, format_stats
from .keyboards import get_pagination_keyboard, get_main_menu, get_filter_buttons
from .config import DEFAULT_LIMIT

# Состояния для ConversationHandler (если нужен пошаговый ввод фильтров)
WAITING_FOR_FILTERS = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Я бот для поиска квартир в аренду в Санкт-Петербурге (данные с BN.ru).\n\n"
        "Используй кнопки или команды:\n"
        "/listings – показать последние объявления\n"
        "/stats – статистика по рынку\n"
        "/search – поиск с фильтрами\n"
        "/help – помощь\n\n"
        "Также можно отправлять команды с параметрами, например:\n"
        "/listings rooms=1 min_price=25000",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/listings [параметры] – список объявлений\n"
        "/stats – статистика\n"
        "/search – интерактивный поиск\n"
        "/start – начать заново\n\n"
        "Параметры для /listings (через пробел):\n"
        "rooms=<0-10> – кол-во комнат (0=студия)\n"
        "min_price=<число>\n"
        "max_price=<число>\n"
        "min_area=<число>\n"
        "max_area=<число>\n"
        "address=<текст>\n"
        "sort_by=price|area|first_seen\n"
        "order=asc|desc\n"
        "limit=<1-20>\n\n"
        "Пример: /listings rooms=1 max_price=40000 limit=5"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    if "error" in stats:
        await update.message.reply_text(f"Ошибка получения статистики: {stats['error']}")
    else:
        await update.message.reply_text(format_stats(stats), parse_mode="Markdown")

async def listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает /listings и параметры в тексте сообщения."""
    # Парсим параметры из текста команды
    text = update.message.text
    params = {}
    # Удаляем "/listings" и извлекаем пары key=value
    parts = text.split()[1:]
    for part in parts:
        if "=" in part:
            key, val = part.split("=", 1)
            if key in ("min_price", "max_price", "min_area", "max_area", "limit"):
                try:
                    params[key] = float(val)
                except:
                    pass
            elif key == "rooms":
                try:
                    params[key] = int(val)
                except:
                    pass
            else:
                params[key] = val
    if "limit" not in params:
        params["limit"] = DEFAULT_LIMIT
    params["page"] = 1

    # Сохраняем параметры в context.user_data для пагинации
    context.user_data["last_params"] = params

    result = get_listings(params)
    if "error" in result:
        await update.message.reply_text(f"Ошибка: {result['error']}")
        return

    items = result.get("items", [])
    total = result.get("total", 0)
    page = result.get("page", 1)
    limit = result.get("limit", DEFAULT_LIMIT)
    total_pages = (total + limit - 1) // limit if total else 1

    if not items:
        await update.message.reply_text("По вашему запросу ничего не найдено.")
        return

    # Формируем сообщение из первых нескольких объявлений (только первое, остальные можно в виде списка)
    # Чтобы не перегружать сообщение, покажем 1 объявление и кнопки для навигации по объявлениям
    # Но лучше показывать список заголовков или по одному с кнопками "далее".
    # Реализуем показ одного объявления с кнопками "Предыдущее/Следующее" и "Новый поиск".
    context.user_data["current_items"] = items
    context.user_data["current_index"] = 0
    context.user_data["total_pages"] = total_pages

    listing = items[0]
    text_msg = format_listing(listing)
    keyboard = [
        [InlineKeyboardButton("▶️ Следующее", callback_data="next_listing")],
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")]
    ]
    if total_pages > 1:
        keyboard.insert(0, [InlineKeyboardButton(f"Страница {page}/{total_pages}", callback_data="ignore")])
    await update.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает интерактивный поиск (выбор фильтров)."""
    await update.message.reply_text(
        "Выберите тип жилья:",
        reply_markup=get_filter_buttons()
    )
    return WAITING_FOR_FILTERS

# Обработчики callback-кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "main_menu":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())
    elif data == "search":
        await query.edit_message_text("Выберите фильтр:", reply_markup=get_filter_buttons())
    elif data == "stats":
        stats = get_stats()
        if "error" in stats:
            await query.edit_message_text(f"Ошибка: {stats['error']}")
        else:
            await query.edit_message_text(format_stats(stats), parse_mode="Markdown")
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("filter_rooms_"):
        rooms_val = data.replace("filter_rooms_", "")
        context.user_data["temp_rooms"] = rooms_val
        # Предложим дополнительные фильтры (цена, площадь) или сразу выполним поиск
        # Для простоты сразу сделаем поиск с выбранными комнатами
        params = {"rooms": int(rooms_val), "limit": DEFAULT_LIMIT, "page": 1}
        result = get_listings(params)
        if "error" in result or not result.get("items"):
            await query.edit_message_text("Ничего не найдено для выбранного типа.")
            return
        items = result["items"]
        context.user_data["last_params"] = params
        context.user_data["current_items"] = items
        context.user_data["current_index"] = 0
        listing = items[0]
        text_msg = format_listing(listing)
        keyboard = [
            [InlineKeyboardButton("▶️ Следующее", callback_data="next_listing")],
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")]
        ]
        await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "next_listing":
        items = context.user_data.get("current_items", [])
        idx = context.user_data.get("current_index", 0)
        if idx + 1 < len(items):
            context.user_data["current_index"] = idx + 1
            listing = items[idx + 1]
            text_msg = format_listing(listing)
            # кнопки те же
            keyboard = [
                [InlineKeyboardButton("◀️ Предыдущее", callback_data="prev_listing")],
                [InlineKeyboardButton("▶️ Следующее", callback_data="next_listing")],
                [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")]
            ]
            if idx == 0:
                keyboard[0].pop(0)  # убрать предыдущее, если это первый
            await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            # если больше нет, загрузить следующую страницу из API
            params = context.user_data.get("last_params", {})
            params["page"] = params.get("page", 1) + 1
            result = get_listings(params)
            if result.get("items"):
                context.user_data["last_params"] = params
                context.user_data["current_items"] = result["items"]
                context.user_data["current_index"] = 0
                listing = result["items"][0]
                text_msg = format_listing(listing)
                total_pages = (result["total"] + result["limit"] - 1) // result["limit"]
                keyboard = [
                    [InlineKeyboardButton(f"Страница {params['page']}/{total_pages}", callback_data="ignore")],
                    [InlineKeyboardButton("▶️ Следующее", callback_data="next_listing")],
                    [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")]
                ]
                await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await query.edit_message_text("Больше объявлений нет.")
    elif data == "prev_listing":
        items = context.user_data.get("current_items", [])
        idx = context.user_data.get("current_index", 0)
        if idx - 1 >= 0:
            context.user_data["current_index"] = idx - 1
            listing = items[idx - 1]
            text_msg = format_listing(listing)
            keyboard = [
                [InlineKeyboardButton("◀️ Предыдущее", callback_data="prev_listing")],
                [InlineKeyboardButton("▶️ Следующее", callback_data="next_listing")],
                [InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")]
            ]
            if idx - 1 == 0:
                keyboard[0].pop(0)  # убрать предыдущее, если это первый
            await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "new_search":
        context.user_data.clear()
        await query.edit_message_text("Начните новый поиск. Используйте /search или /listings.", reply_markup=get_main_menu())
    elif data == "ignore":
        pass  # просто игнорируем нажатие на информационную кнопку

        