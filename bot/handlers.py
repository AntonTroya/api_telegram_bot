import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils import get_listings, get_stats, format_listing, format_stats
from bot.keyboards import get_main_menu, get_filter_buttons
from bot.config import DEFAULT_LIMIT

WAITING_FOR_FILTERS = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для поиска аренды квартир в Санкт-Петербурге.\n\n"
        "Вы можете использовать кнопки на клавиатуре или команды:\n"
        "/listings – показать последние предложения\n"
        "/stats – статистика рынка\n"
        "/search – запустить быстрые фильтры\n"
        "/help – доступные параметры поиска",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 *Параметры для ручного поиска /listings (через пробел):*\n\n"
        "• `rooms=<число>` — комнат (0 - студия)\n"
        "• `min_price=<число>` — минимальная цена\n"
        "• `max_price=<число>` — максимальная цена\n"
        "• `min_area=<число>`\n"
        "• `max_area=<число>`\n"
        "• `limit=<1-20>` — результатов на странице\n\n"
        "*Пример:* `/listings rooms=1 max_price=45000 limit=5`",
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    if "error" in stats:
        await update.message.reply_text(f"Ошибка получения статистики: {stats['error']}")
    else:
        await update.message.reply_text(format_stats(stats), parse_mode="Markdown")

async def listings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    params = {}
    parts = text.split()[1:]
    
    for part in parts:
        if "=" in part:
            key, val = part.split("=", 1)
            if key in ("min_price", "max_price", "min_area", "max_area", "limit"):
                try:
                    params[key] = float(val)
                except ValueError:
                    pass
            elif key == "rooms":
                try:
                    params[key] = int(val)
                except ValueError:
                    pass
            else:
                params[key] = val
                
    if "limit" not in params:
        params["limit"] = DEFAULT_LIMIT
    params["page"] = 1

    context.user_data["last_params"] = params
    await process_and_send_listings(update, context, params)

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите тип жилья:", reply_markup=get_filter_buttons())
    return WAITING_FOR_FILTERS

async def process_and_send_listings(update_or_query, context: ContextTypes.DEFAULT_TYPE, params: dict, is_callback: bool = False):
    result = get_listings(params)
    send_method = update_or_query.edit_message_text if is_callback else update_or_query.message.reply_text

    if "error" in result:
        await send_method(f"Произошла ошибка при получении данных: {result['error']}")
        return

    items = result.get("items", [])
    total = result.get("total", 0)
    page = params.get("page", 1)
    limit = params.get("limit", DEFAULT_LIMIT)
    total_pages = (total + limit - 1) // limit if total else 1

    if not items:
        await send_method("Объявления по вашему запросу отсутствуют.")
        return

    context.user_data["current_items"] = items
    context.user_data["current_index"] = 0
    context.user_data["total_pages"] = total_pages

    listing = items[0]
    text_msg = format_listing(listing)
    
    keyboard = []
    nav_row = []
    if len(items) > 1:
        nav_row.append(InlineKeyboardButton("▶️ След.", callback_data="next_listing"))
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([InlineKeyboardButton(f"Страница {page}/{total_pages}", callback_data="ignore")])
    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])

    await send_method(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "main_menu":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu())
    elif data == "search":
        await query.edit_message_text("Выберите количество комнат:", reply_markup=get_filter_buttons())
    elif data == "stats":
        stats = get_stats()
        if "error" in stats:
            await query.edit_message_text(f"Ошибка: {stats['error']}")
        else:
            await query.edit_message_text(format_stats(stats), reply_markup=get_main_menu(), parse_mode="Markdown")
    elif data == "help":
        await query.edit_message_text(
            "Параметры для ручного поиска `/listings`:\n"
            "`rooms=X`, `max_price=Y`, `limit=Z`\n\n"
            "Пример: `/listings rooms=0 max_price=30000`",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
    elif data.startswith("filter_rooms_"):
        rooms_val = int(data.replace("filter_rooms_", ""))
        params = {"rooms": rooms_val, "limit": DEFAULT_LIMIT, "page": 1}
        context.user_data["last_params"] = params
        await process_and_send_listings(query, context, params, is_callback=True)
        
    elif data == "next_listing":
        items = context.user_data.get("current_items", [])
        idx = context.user_data.get("current_index", 0)
        
        if idx + 1 < len(items):
            context.user_data["current_index"] = idx + 1
            listing = items[idx + 1]
            text_msg = format_listing(listing)
            
            keyboard = [[
                InlineKeyboardButton("◀️ Пред.", callback_data="prev_listing"),
                InlineKeyboardButton("▶️ След.", callback_data="next_listing")
            ]]
            if idx + 2 == len(items):
                keyboard[0].pop(1)
            keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])
            await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            params = context.user_data.get("last_params", {})
            params["page"] = params.get("page", 1) + 1
            context.user_data["last_params"] = params
            await process_and_send_listings(query, context, params, is_callback=True)
            
    elif data == "prev_listing":
        items = context.user_data.get("current_items", [])
        idx = context.user_data.get("current_index", 0)
        
        if idx - 1 >= 0:
            context.user_data["current_index"] = idx - 1
            listing = items[idx - 1]
            text_msg = format_listing(listing)
            
            keyboard = [[
                InlineKeyboardButton("◀️ Пред.", callback_data="prev_listing"),
                InlineKeyboardButton("▶️ След.", callback_data="next_listing")
            ]]
            if idx - 1 == 0:
                keyboard[0].pop(0)
            keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])
            await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            
    elif data == "new_search":
        context.user_data.clear()
        await query.edit_message_text("Начните новый поиск:", reply_markup=get_main_menu())
        