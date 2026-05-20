"""
Парсинг карточек объявлений BN.ru – надёжное извлечение цены
"""
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

def extract_numeric(text: str) -> Optional[float]:
    """Извлекает число из строки, игнорируя пробелы, валюту, лишние символы."""
    if not text:
        return None
    # Убираем пробелы, неразрывные пробелы, заменяем запятую на точку
    cleaned = text.replace(" ", "").replace("\xa0", "").replace(",", ".")
    # Ищем целое или дробное число (точка как разделитель)
    match = re.search(r'\d+\.?\d*', cleaned)
    if match:
        return float(match.group())
    return None

def parse_listing_card(html_or_element, debug_first: bool = False) -> Dict[str, Any]:
    """
    Парсит одну карточку объявления.
    Возвращает словарь с ключами: title, price, address, area, rooms, floor, link.
    """
    if hasattr(html_or_element, 'get_attribute'):
        html = html_or_element.get_attribute('outerHTML')
    else:
        html = html_or_element
    soup = BeautifulSoup(html, 'html.parser')

    data = {
        "title": None,
        "price": None,
        "address": None,
        "area": None,
        "rooms": None,
        "floor": None,
        "link": None,
    }

    # ---- Ссылка ----
    link_el = soup.select_one("a.catalog-item")
    if link_el and link_el.get("href"):
        href = link_el.get("href")
        data["link"] = href if href.startswith("http") else "https://www.bn.ru" + href

    # ---- Заголовок ----
    title_el = soup.select_one("div.catalog-item__headline")
    if title_el:
        data["title"] = title_el.get_text(strip=True)

    # ---- ЦЕНА (главное исправление) ----
    # Пробуем несколько селекторов
    price_el = None
    for selector in [
        "div.catalog-item__price",           # основной класс
        "span[class*='price']",              # любой span с 'price' в классе
        "div[class*='price']:not([class*='unit'])",  # не единица измерения
        "div.catalog-item__price-new",       # иногда для акций
        "[data-testid='price']"              # возможный атрибут
    ]:
        price_el = soup.select_one(selector)
        if price_el:
            break

    if price_el:
        price_text = price_el.get_text(strip=True)
        # Пример текста: "25 000 ₽", "25.000₽", "25000 руб."
        data["price"] = extract_numeric(price_text)
        if debug_first:
            print(f"[DEBUG] Цена из '{price_text}' -> {data['price']}")
    else:
        # Если не нашли цену по селекторам, ищем любой элемент, похожий на цену (содержит цифры и символ рубля)
        all_text = soup.get_text()
        matches = re.findall(r'(\d{1,3}(?:[ \xa0]?\d{3})*)(?:\.\d+)?\s*[₽руб]', all_text)
        if matches:
            # Берём первое число, которое похоже на цену (обычно это самая крупная сумма)
            candidate = matches[0].replace(" ", "").replace("\xa0", "")
            data["price"] = extract_numeric(candidate)
            if debug_first:
                print(f"[DEBUG] Цена (fallback) из текста '{candidate}' -> {data['price']}")

    # ---- Адрес ----
    address_el = soup.select_one("div.catalog-item__address")
    if address_el:
        data["address"] = address_el.get_text(strip=True)

    # ---- Площадь и комнаты из заголовка ----
    if data["title"]:
        title_lower = data["title"].lower()
        # Площадь: "65.00 м2" или "65 м²"
        area_match = re.search(r'(\d+[,.]?\d*)\s*м[2²]', title_lower)
        if area_match:
            data["area"] = extract_numeric(area_match.group(1))
        # Комнаты
        if "студия" in title_lower:
            data["rooms"] = 0
        else:
            rooms_match = re.search(r'(\d+)\s*[-к]', title_lower)
            if not rooms_match:
                rooms_match = re.search(r'(\d+)\s*комн', title_lower)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

    # ---- Этаж ----
    param_spans = soup.select("span.catalog-item__param")
    for param in param_spans:
        text = param.get_text(strip=True)
        if 'этаж' in text.lower():
            value_el = param.select_one("span.catalog-item__param-value")
            if value_el:
                data["floor"] = value_el.get_text(strip=True)
            else:
                match = re.search(r'(\d+/\d+)', text)
                if match:
                    data["floor"] = match.group(1)
            break

    return data

