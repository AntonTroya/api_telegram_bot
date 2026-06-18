import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

def extract_numeric(text: str) -> Optional[float]:
    if not text:
        return None
    
    # 1. Удаляем пробелы разрядов внутри чисел (например, "60 000" -> "60000")
    cleaned = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
    cleaned = cleaned.replace(" ", "").replace("\xa0", "")
    
    # 2. Находим первое непрерывное число (чтобы избежать сложения с доп. платежами КУ)
    match = re.search(r'\d+[\.,]?\d*', cleaned)
    if match:
        num_str = match.group().replace(',', '.')
        try:
            return float(num_str)
        except ValueError:
            return None
    return None

def extract_district(address: str) -> str:
    if not address:
        return "Не указан"
    districts = [
        'Адмиралтейский', 'Василеостровский', 'Выборгский', 'Калининский',
        'Кировский', 'Красногвардейский', 'Красносельский', 'Московский',
        'Невский', 'Петроградский', 'Приморский', 'Фрунзенский', 'Центральный'
    ]
    address_lower = address.lower()
    for district in districts:
        if district.lower() in address_lower:
            return district
        # Резервный поиск без окончаний (например, "Василеостровская")
        if district[:-2].lower() in address_lower:
            return district
    return "Другой"

def parse_listing_card(html_or_element, debug_first: bool = False) -> Dict[str, Any]:
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
        "district": "Не указан"
    }

    # Поиск ссылки
    link_el = soup.select_one("a.catalog-item")
    if not link_el:
        link_el = soup.find('a', href=re.compile(r'/detail/|/flat/|/kvartiry/'))
    if link_el:
        href = link_el.get("href")
        if href:
            data["link"] = href if href.startswith("http") else "https://www.bn.ru" + href

    # Поиск заголовка
    title_el = soup.select_one("div.catalog-item__headline")
    if not title_el and link_el:
        title_el = link_el
    if title_el:
        data["title"] = title_el.get_text(strip=True)

    # Извлечение и парсинг цены
    price_el = soup.select_one("div.catalog-item__price")
    if not price_el:
        price_el = soup.select_one("[class*='price']:not([class*='unit']):not([class*='firm'])")
    if price_el:
        price_text = price_el.get_text(strip=True)
        data["price"] = extract_numeric(price_text)
        if debug_first and data["price"]:
            print(f"[DEBUG] Цена: '{price_text}' -> {data['price']}")

    # Адрес и сопоставление с районом
    address_el = soup.select_one("div.catalog-item__address")
    if address_el:
        data["address"] = address_el.get_text(strip=True)
        data["district"] = extract_district(data["address"])

    # Извлечение площади и комнатности
    if data["title"]:
        title_text = data["title"]
        area_match = re.search(r'(\d+[,.]?\d*)\s*(?:кв\.?\s*м\.?|м[2²]|м2)', title_text, re.IGNORECASE)
        if area_match:
            data["area"] = extract_numeric(area_match.group(1))
        
        if 'студия' in title_text.lower():
            data["rooms"] = 0
        else:
            rooms_match = re.search(r'(\d+)\s*[-к]', title_text, re.IGNORECASE)
            if not rooms_match:
                rooms_match = re.search(r'(\d+)\s*комн', title_text, re.IGNORECASE)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

    # Извлечение этажа
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

    if not data["floor"]:
        full_text = soup.get_text(separator=" ", strip=True)
        floor_match = re.search(r'(\d+/\d+)\s*(?:эт\.?|этаж)', full_text, re.IGNORECASE)
        if floor_match:
            data["floor"] = floor_match.group(1)

    return data
