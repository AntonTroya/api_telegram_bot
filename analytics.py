"""
Модуль локальной аналитики и построения графиков на базе СУБД SQLite
"""
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from config import RAW_DATA_PATH, REPORTS_DIR

def generate_reports():
    print("Чтение данных из SQL...")
    
    with sqlite3.connect(RAW_DATA_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT district, price, area FROM listings WHERE is_active = 1 AND price IS NOT NULL AND price > 0", 
            conn
        )
        
    if df.empty:
        print("База данных не содержит активных объявлений с ценой.")
        return
        
    df['price_per_sqm'] = df['price'] / df['area']
    df = df[df['district'] != 'Не указан']

    # Группировка по районам
    district_stats = df.groupby('district').agg(
        avg_price=('price', 'mean'),
        avg_price_sqm=('price_per_sqm', 'mean'),
        count=('price', 'count')
    ).reset_index()

    # Сортировка по убыванию стоимости квадратного метра
    district_stats = district_stats.sort_values(by='avg_price_sqm', ascending=False)

    # Построение горизонтального столбчатого графика
    plt.figure(figsize=(12, 7))
    bars = plt.barh(district_stats['district'], district_stats['avg_price_sqm'] / 1000, color='#3498db', edgecolor='grey')
    
    plt.xlabel('Средняя цена за кв. м (тыс. руб.)', fontsize=12)
    plt.ylabel('Район', fontsize=12)
    plt.title('Распределение средней стоимости квадратного метра по районам СПБ', fontsize=14, pad=15)
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1.5, bar.get_y() + bar.get_height()/2, f'{width:.1f} т.р.', 
                 va='center', ha='left', fontsize=9)

    plt.tight_layout()
    
    # Сохранение графика в отчеты
    report_path = REPORTS_DIR / "district_prices.png"
    plt.savefig(report_path, dpi=150)
    plt.close()
    
    print(f"График успешно сформирован и сохранен в: {report_path}")
    print("\nСтатистика по районам Санкт-Петербурга:")
    print(district_stats.to_string(index=False))

if __name__ == "__main__":
    generate_reports()
    