#!/usr/bin/env python
"""
Telegram-бот для получения данных об аренде квартир.
Запуск: python -m bot.bot
"""
import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler
)
from .config import TOKEN
from .handlers import (
    start, help_command, stats_command, listings_command,
    search_start, button_callback, WAITING_FOR_FILTERS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("listings", listings_command))

    # Интерактивный поиск через ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            WAITING_FOR_FILTERS: [CallbackQueryHandler(button_callback)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    application.add_handler(conv_handler)

    # Общий обработчик кнопок (для всех callback)
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()

    