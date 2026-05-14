from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class Product(Document):
    asin: str = Field(..., description="Amazon product ASIN")
    title: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    price_display: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    rating: Optional[float] = None
    stock: Optional[str] = None
    url: Optional[str] = None
    scraped_url: Optional[str] = None
    amazon_domain: Optional[str] = None
    geo_location: Optional[str] = None
    scraped_at: Optional[datetime] = None
    images: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    category_path: List[str] = Field(default_factory=list)
    product_overview: List[str] = Field(default_factory=list)
    buybox: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "products"
        indexes = [
            [("asin", 1), ("geo_location", 1)],
            "asin",
            "brand",
            "amazon_domain",
            "geo_location",
        ]


class PriceHistory(Document):
    asin: str = Field(..., description="Amazon product ASIN")
    price: Optional[float] = None
    currency: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "price_history"
        indexes = [
            "asin",
            "timestamp",
        ]