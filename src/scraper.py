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
        
        title_elem = soup.find("span", {"id": "productTitle"})
        if title_elem:
            product_data["title"] = title_elem.get_text(strip=True)
        
        price_elem = soup.find("span", class_=re.compile("a-price-whole"))
        
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_value = self._parse_price(price_text)
            product_data["price"] = price_value
            
            if price_value is not None:
                product_data["price_display"] = f"{currency_symbol}{price_value}"
        
        brand_elem = soup.find("a", {"id": "brandByline"})
        if brand_elem:
            product_data["brand"] = brand_elem.get_text(strip=True)
        
        rating_elem = soup.find("span", class_=re.compile("a-icon-alt"))
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                try:
                    product_data["rating"] = float(rating_match.group(1))
                except:
                    pass
        
        images = []
        img_elements = soup.find_all("img", {"data-a-image-name": re.compile("landingImage|mainImage")})
        for img in img_elements[:5]:
            src = img.get("src") or img.get("data-src")
            if src:
                images.append(src)
        product_data["images"] = images
        
        categories = []
        breadcrumb = soup.find("div", {"id": "wayfinding-breadcrumbs_feature_div"})
        if breadcrumb:
            links = breadcrumb.find_all("a")
            categories = [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
        product_data["categories"] = categories
        product_data["category_path"] = categories
        
        overview_items = []
        overview = soup.find("div", {"id": "feature-bullets"})
        if overview:
            bullets = overview.find_all("span", class_="a-list-item")
            overview_items = [bullet.get_text(strip=True) for bullet in bullets if bullet.get_text(strip=True)]
        product_data["product_overview"] = overview_items
        
        stock_elem = soup.find("div", {"id": "availability"})
        if stock_elem:
            product_data["stock"] = stock_elem.get_text(strip=True)
        
        if not is_valid_product(product_data):
            raise ValueError(f"Product {asin} appears to be empty or invalid. Missing required fields (title, price, or brand).")
        
        return product_data