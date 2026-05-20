"""
Скрапер объявлений с BN.ru (Санкт-Петербург, аренда квартир) 
"""
import random
import time
import sqlite3
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

from .config import (
    BN_CONFIG, SELECTORS, DELAYS, RAW_DATA_PATH,
    SELENIUM_OPTIONS, PROXY
)
from .parser import parse_listing_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BnScraper:
    """Скрапер для BN.ru"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self._setup_driver()
        self._init_db()

    def _setup_driver(self):
        chrome_options = Options()
        for option in SELENIUM_OPTIONS:
            chrome_options.add_argument(option)
        if self.headless:
            chrome_options.add_argument("--headless")

        if PROXY.get("server"):
            chrome_options.add_argument(f'--proxy-server={PROXY["server"]}')

        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(options=chrome_options, service=service)

        stealth(
            self.driver,
            languages=["ru-RU", "ru"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        self.wait = WebDriverWait(self.driver, DELAYS["element_wait"])

    def _init_db(self):
        RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(RAW_DATA_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    price REAL,
                    address TEXT,
                    area REAL,
                    rooms INTEGER,
                    floor TEXT,
                    link TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        logger.info("База данных инициализирована")

    def _build_url(self, page: int = 1) -> str:
        base = BN_CONFIG["base_url"] + BN_CONFIG["search_path"]
        if page > 1:
            return f"{base}?page={page}"
        return base

    def _scroll_page(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
        try:
            # Ожидаем появления заголовков (значит, контент загрузился)
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.catalog-item__headline"))
            )
        except TimeoutException:
            logger.warning("Контент карточек не загрузился после скролла")

    def _extract_listings_from_page(self) -> List[Dict[str, Any]]:
        listings = []
        containers = self.driver.find_elements(By.CSS_SELECTOR, SELECTORS["listing_card"])
        logger.info(f"Найдено контейнеров: {len(containers)}")
        if not containers:
            logger.warning("Контейнеры не найдены")
            return listings

        for container in containers:
            try:
                data = parse_listing_card(container)
                if data["link"]:
                    listings.append(data)
            except Exception as e:
                logger.warning(f"Ошибка парсинга контейнера: {e}")
        return listings

    @staticmethod
    def _extract_id_from_url(url: str) -> Optional[str]:
        match = re.search(r"/arenda/(\d+)", url)
        return match.group(1) if match else None

    def _save_listings(self, listings: List[Dict[str, Any]]):
        now = datetime.now().isoformat()
        with sqlite3.connect(RAW_DATA_PATH) as conn:
            cur = conn.cursor()
            for lst in listings:
                listing_id = self._extract_id_from_url(lst["link"])
                if not listing_id:
                    continue
                cur.execute("SELECT id FROM listings WHERE id = ?", (listing_id,))
                exists = cur.fetchone()
                if exists:
                    cur.execute("""
                        UPDATE listings
                        SET price = ?, last_seen = ?, is_active = 1
                        WHERE id = ?
                    """, (lst["price"], now, listing_id))
                else:
                    cur.execute("""
                        INSERT INTO listings
                        (id, title, price, address, area, rooms, floor, link, first_seen, last_seen, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        listing_id,
                        lst["title"],
                        lst["price"],
                        lst["address"],
                        lst["area"],
                        lst["rooms"],
                        lst["floor"],
                        lst["link"],
                        now,
                        now,
                    ))
            conn.commit()
        logger.info(f"Сохранено {len(listings)} объявлений")

    def _go_to_next_page(self) -> bool:
        try:
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTORS["next_page"]))
            )
            next_btn.click()
            time.sleep(DELAYS["between_pages"] + random.uniform(1, 2))
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def scrape(self, max_pages: int = None) -> int:
        max_pages = max_pages or BN_CONFIG["max_pages"]
        total = 0
        try:
            for page in range(1, max_pages + 1):
                url = self._build_url(page)
                logger.info(f"Страница {page}: {url}")
                self.driver.get(url)
                time.sleep(DELAYS["page_load"] + random.uniform(1, 3))

                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.catalog-item__headline"))
                    )
                except TimeoutException:
                    logger.warning("Данные не загрузились на странице")
                    break

                self._scroll_page()
                listings = self._extract_listings_from_page()
                self._save_listings(listings)
                total += len(listings)
                logger.info(f"Собрано {len(listings)} объявлений")

                if not self._go_to_next_page():
                    logger.info("Пагинация закончилась")
                    break
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            raise
        finally:
            self.driver.quit()
        logger.info(f"Общий сбор: {total} объявлений")
        return total


def main():
    scraper = BnScraper(headless=False)
    scraper.scrape()


if __name__ == "__main__":
    main()
    