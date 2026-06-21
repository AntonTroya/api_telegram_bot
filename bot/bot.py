import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler
)
from bot.config import TOKEN
from bot.handlers import (
    start, help_command, stats_command, listings_command,
    search_start, button_callback, WAITING_FOR_FILTERS
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    if not TOKEN:
        logger.error("Токен бота не найден. Проверьте конфигурационный файл .env")
        return

    # Настройка приложения на базе API-токена
    application = ApplicationBuilder().token(TOKEN).build()

    # Текстовые обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("listings", listings_command))

    # Диалоговые цепочки инлайн-поиска
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            WAITING_FOR_FILTERS: [CallbackQueryHandler(button_callback)]
        },
        fallbacks=[CommandHandler("start", start)]
    )
    application.add_handler(conv_handler)

    # Общие callback-события нажатия кнопок
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Бот запущен. Ожидание сообщений от пользователей...")
    application.run_polling()

if __name__ == "__main__":
    main()
    