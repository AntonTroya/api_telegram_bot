"""
Prefect Flow для периодического скрапинга и анализа данных (BN.ru)
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from prefect import flow, task

from scraper.bn_scraper import BnScraper
from scraper.config import RAW_DATA_PATH, PROCESSED_DATA_PATH


@task
def scrape_new_listings() -> int:
    """Сбор новых объявлений"""
    scraper = BnScraper(headless=True)
    return scraper.scrape()


@task
def update_inactive_listings():
    """Помечаем неактивные объявления (не обновлялись более 3 дней)"""
    with sqlite3.connect(RAW_DATA_PATH) as conn:
        cursor = conn.cursor()
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        cursor.execute("""
            UPDATE listings
            SET is_active = 0
            WHERE last_seen < ?
        """, (three_days_ago,))
        conn.commit()
        deactivated = cursor.rowcount
    return deactivated


@task
def generate_daily_stats():
    """Генерация агрегированной статистики за день"""
    with sqlite3.connect(RAW_DATA_PATH) as conn:
        query = """
        SELECT
            DATE(first_seen) as date,
            COUNT(*) as new_listings,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(area) as avg_area
        FROM listings
        GROUP BY DATE(first_seen)
        ORDER BY date DESC
        """
        df = pd.read_sql_query(query, conn)

    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PROCESSED_DATA_PATH.exists():
        existing_df = pd.read_csv(PROCESSED_DATA_PATH)
        df = pd.concat([df, existing_df]).drop_duplicates(subset=["date"])
    df.to_csv(PROCESSED_DATA_PATH, index=False)

    if not df.empty:
        return df.tail(1).iloc[0].to_dict()
    return {}


@task
def log_metrics(new_listings: int, deactivated: int, stats: dict):
    """Логирование результатов"""
    print(f"=== Результаты запуска {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print(f"Собрано новых объявлений: {new_listings}")
    print(f"Помечено неактивных: {deactivated}")
    if stats.get("avg_price") is not None:
        print(f"Средняя цена сегодня: {stats['avg_price']:,.0f} руб.")
    print("=" * 50)


@flow(name="bn-spb-monitoring", log_prints=True)
def monitoring_flow():
    """Основной Flow для мониторинга рынка аренды Санкт-Петербурга (BN.ru)"""
    new_listings = scrape_new_listings()
    deactivated = update_inactive_listings()
    stats = generate_daily_stats()
    log_metrics(new_listings, deactivated, stats)

    return {
        "new_listings": new_listings,
        "deactivated": deactivated,
        "stats": stats
    }


if __name__ == "__main__":
    monitoring_flow()


    