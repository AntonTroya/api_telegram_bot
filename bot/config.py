import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")

API_BASE_URL = "http://127.0.0.1:8000"  # адрес запущенного API
DEFAULT_LIMIT = 5
MAX_LIMIT = 20

