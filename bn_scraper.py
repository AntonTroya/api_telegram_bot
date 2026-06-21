import random
import time
import sqlite3
import logging
import re
import csv
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

try:
    from config import (
        BN_CONFIG, SELECTORS, DELAYS, RAW_DATA_PATH, PROCESSED_DATA_PATH,
        REPORTS_DIR, SELENIUM_OPTIONS, PROXY
    )
    from parser import parse_listing_card
except ImportError:
    from .config import (
        BN_CONFIG, SELECTORS, DELAYS, RAW_DATA_PATH, PROCESSED_DATA_PATH,
        REPORTS_DIR, SELENIUM_OPTIONS, PROXY
    )
    from .parser import parse_listing_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BnScraper:
    """Скрапер долгосрочной аренды BN.ru с аналитикой"""

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

        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

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
                    district TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        logger.info("База данных SQL инициализирована.")

    def _build_url(self, page: int = 1) -> str:
        base = BN_CONFIG["base_url"] + BN_CONFIG["search_path"]
        if page > 1:
            return f"{base}?page={page}"
        return base

    def _scroll_page(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.catalog-item__headline, div.catalog-item"))
            )
        except TimeoutException:
            logger.warning("Элементы контента не появились в DOM после прокрутки.")

    def _extract_listings_from_page(self) -> List[Dict[str, Any]]:
        listings = []
        containers = self.driver.find_elements(By.CSS_SELECTOR, SELECTORS["listing_card"])
        logger.info(f"Найдено контейнеров на странице: {len(containers)}")
        
        for container in containers:
            try:
                data = parse_listing_card(container)
                if data["link"]:
                    listings.append(data)
            except Exception as e:
                logger.warning(f"Ошибка извлечения данных из контейнера: {e}")
        return listings

    @staticmethod
    def _extract_id_from_url(url: str) -> Optional[str]:
        if not url:
            return None
        match = re.search(r'/(\d+)/?$', url)
        if not match:
            match = re.search(r'/detail/[^/]*/(\d+)', url)
        return match.group(1) if match else None

    def _save_listings(self, listings: List[Dict[str, Any]]):
        now = datetime.now().isoformat()
        saved_count = 0
        with sqlite3.connect(RAW_DATA_PATH) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE listings SET is_active = 0")
            
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
                        (id, title, price, address, area, rooms, floor, link, district, first_seen, last_seen, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        listing_id,
                        lst["title"],
                        lst["price"],
                        lst["address"],
                        lst["area"],
                        lst["rooms"],
                        lst["floor"],
                        lst["link"],
                        lst.get("district", "Не указан"),
                        now,
                        now,
                    ))
                saved_count += 1
            conn.commit()
        logger.info(f"Сохранено новых и обновлено записей: {saved_count}")

    def update_daily_stats_csv(self):
        """Анализ собранных предложений и выгрузка метрик в CSV"""
        PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(RAW_DATA_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price, area FROM listings 
                WHERE is_active = 1 AND price IS NOT NULL AND price > 0
            """)
            rows = cursor.fetchall()
            
        if not rows:
            logger.warning("Нет активных объявлений для расчета статистики.")
            return

        total_listings = len(rows)
        avg_price = sum(r[0] for r in rows) / total_listings
        
        valid_areas = [r for r in rows if r[1] and r[1] > 0]
        avg_sqm_price = (
            sum(r[0] / r[1] for r in valid_areas) / len(valid_areas)
            if valid_areas else 0
        )
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_exists = PROCESSED_DATA_PATH.exists()
        
        with open(PROCESSED_DATA_PATH, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['date', 'total_listings', 'avg_price', 'avg_price_per_sqm'])
            writer.writerow([date_str, total_listings, round(avg_price, 2), round(avg_sqm_price, 2)])
            
        logger.info(f"Статистика внесена в файл отчетов {PROCESSED_DATA_PATH.name}")

    def generate_district_chart(self):
        """Генерация графика средней стоимости аренды по районам"""
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(RAW_DATA_PATH) as conn:
                df = pd.read_sql_query("""
                    SELECT district, price FROM listings 
                    WHERE is_active = 1 AND price IS NOT NULL AND price > 0 AND district != 'Не указан'
                """, conn)
                
            if df.empty:
                logger.warning("Недостаточно записей в БД для построения графиков.")
                return

            district_avg = df.groupby('district')['price'].mean().sort_values(ascending=False).reset_index()
            
            plt.figure(figsize=(10, 6))
            bars = plt.barh(district_avg['district'], district_avg['price'] / 1000, color='#3498db', edgecolor='grey')
            plt.xlabel('Средняя стоимость аренды (тыс. руб. / мес.)', fontsize=11)
            plt.ylabel('Район', fontsize=11)
            plt.title('Распределение цен на аренду квартир по районам Санкт-Петербурга', fontsize=13, pad=15)
            plt.grid(axis='x', linestyle='--', alpha=0.5)
            
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:.1f} т.р.', 
                         va='center', ha='left', fontsize=9)
            
            plt.tight_layout()
            chart_path = REPORTS_DIR / "district_prices.png"
            plt.savefig(chart_path, dpi=150)
            plt.close()
            logger.info(f"Аналитический график сохранен: {chart_path}")
        except ImportError:
            logger.warning("Построение графиков отменено: отсутствуют pandas или matplotlib.")

    def scrape(self, max_pages: int = None) -> int:
        max_pages = max_pages or BN_CONFIG["max_pages"]
        total = 0
        try:
            for page in range(1, max_pages + 1):
                url = self._build_url(page)
                logger.info(f"Обработка страницы {page}/{max_pages}: {url}")
                self.driver.get(url)
                time.sleep(DELAYS["page_load"] + random.uniform(1, 3))

                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.catalog-item__headline, div.catalog-item"))
                    )
                except TimeoutException:
                    logger.warning(f"Контент не загрузился на странице {page}. Обход окончен.")
                    break

                self._scroll_page()
                listings = self._extract_listings_from_page()
                
                # Проверка успешности извлечения цен
                valid_prices = sum(1 for item in listings if item.get("price") is not None)
                logger.info(f"Распознано цен на странице: {valid_prices} из {len(listings)}")
                
                if not listings:
                    logger.info("Список объявлений на странице пуст. Завершение работы.")
                    break
                    
                self._save_listings(listings)
                total += len(listings)
                
                # Задержка между запросами во избежание блокировок
                if page < max_pages:
                    time.sleep(random.uniform(DELAYS["between_pages"], DELAYS["between_pages"] + 1))
        except Exception as e:
            logger.error(f"Произошла ошибка при выполнении: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
        
        # Постобработка и аналитика
        self.update_daily_stats_csv()
        self.generate_district_chart()
        
        logger.info(f"Сбор данных успешно завершен. Всего найдено: {total} объектов.")
        return total


def main():
    scraper = BnScraper(headless=False)
    scraper.scrape()


if __name__ == "__main__":
    main()
    