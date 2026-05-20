"""
Пакет для скрапинга данных с BN.ru
"""

from .bn_scraper import BnScraper
from .parser import parse_listing_card

__all__ = ["BnScraper", "parse_listing_card"]

