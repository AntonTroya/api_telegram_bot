"""
Конфигурация для скрапера BN.ru (Санкт-Петербург, аренда квартир)
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

BN_CONFIG = {
    "base_url": "https://www.bn.ru",
    "search_path": "/arenda-kvartiry/",
    "city_name": "Санкт-Петербург",
    "deal_type": "rent",
    "offer_type": "flat",
    "max_pages": 3,
    "max_ads_per_page": 30,
}

SELECTORS = {
    "listing_card": "div[class*='catalog-item__container'], div.catalog-item", 
    "title": "div.catalog-item__headline",
    "price": "div.catalog-item__price",
    "address": "div.catalog-item__address",
}

DELAYS = {
    "page_load": 4,
    "between_pages": 3,
    "element_wait": 10,
}

RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "spb_rentals.db"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "daily_stats.csv"
REPORTS_DIR = BASE_DIR / "reports"

SELENIUM_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
]

PROXY = {
    "server": "",
}
