from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import re
from datetime import datetime
from .proxy_client import ThordataProxyClient
from .currency_utils import get_amazon_domain, get_country_currency, get_currency_symbol
from .product_validator import is_valid_product


class AmazonScraper:
    def __init__(self):
        self.proxy_client = ThordataProxyClient()

    def _parse_price(self, price_text: str) -> Optional[float]:
        if not price_text:
            return None
        
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(",", ""))
        if price_match:
            try:
                return float(price_match.group().replace(",", ""))
            except:
                return None
        return None

    def scrape_product(self, asin: str, country_code: str) -> Dict[str, Any]:
        domain = get_amazon_domain(country_code)
        url = f"https://www.amazon.{domain}/dp/{asin}"
        
        response = self.proxy_client.get(url, country=country_code)
        response.raise_for_status()
        
        scraped_url = response.url
        soup = BeautifulSoup(response.content, "lxml")
        
        currency_code = get_country_currency(country_code)
        currency_symbol = get_currency_symbol(currency_code)
        
        product_data = {
            "asin": asin,
            "url": url,
            "scraped_url": scraped_url,
            "amazon_domain": domain,
            "geo_location": country_code.upper(),
            "currency": currency_code,
            "currency_symbol": currency_symbol,
            "scraped_at": datetime.now().isoformat()
        }