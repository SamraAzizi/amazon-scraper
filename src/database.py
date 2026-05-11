import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from .models import Product, PriceHistory
from .product_validator import is_valid_product


class Database:
    _client: Optional[AsyncIOMotorClient] = None
    _initialized: bool = False

    def __init__(self):
        self.connection_string = os.getenv(
            "MONGODB_URL", 
            "mongodb://localhost:27017"
        )
        self.database_name = os.getenv("MONGODB_DATABASE", "amazon_price_agent")

    async def initialize(self):
        if not Database._initialized:
            Database._client = AsyncIOMotorClient(self.connection_string)
            await init_beanie(
                database=Database._client[self.database_name],
                document_models=[Product, PriceHistory]
            )
            Database._initialized = True

    async def insert_or_update_product(self, product_data: Dict[str, Any]) -> str:
        await self.initialize()
        
        asin = product_data.get("asin")
        geo_location = product_data.get("geo_location")
        
        if not asin:
            raise ValueError("ASIN is required")
        if not geo_location:
            raise ValueError("geo_location is required")
        
        if not is_valid_product(product_data):
            raise ValueError(f"Product {asin} appears to be empty or invalid. Missing required fields (title, price, or brand).")
        
        product_dict = {k: v for k, v in product_data.items() if v is not None}
        
        if "scraped_at" in product_dict and isinstance(product_dict["scraped_at"], str):
            try:
                product_dict["scraped_at"] = datetime.fromisoformat(product_dict["scraped_at"])
            except (ValueError, TypeError):
                product_dict["scraped_at"] = datetime.now()
        elif "scraped_at" not in product_dict:
            product_dict["scraped_at"] = datetime.now()
        
        product_dict["updated_at"] = datetime.now()
        
        existing_product = await Product.find_one(
            Product.asin == asin,
            Product.geo_location == geo_location
        )
        
        if existing_product:
            for key, value in product_dict.items():
                setattr(existing_product, key, value)
            existing_product.updated_at = datetime.now()
            await existing_product.save()
            product = existing_product
        else:
            product_dict["created_at"] = datetime.now()
            product = Product(**product_dict)
            await product.insert()
        
        if product_data.get("price") is not None:
            price_history = PriceHistory(
                asin=asin,
                price=product_data.get("price"),
                currency=product_data.get("currency"),
                timestamp=datetime.now()
            )
            await price_history.insert()
        
        return asin

    async def get_product(self, asin: str, geo_location: str = None) -> Optional[Dict[str, Any]]:
        await self.initialize()
        if geo_location:
            product = await Product.find_one(
                Product.asin == asin,
                Product.geo_location == geo_location.upper()
            )
        else:
            product = await Product.find_one(Product.asin == asin)
        if product:
            return product.model_dump()
        return None

    async def get_price_history(self, asin: str, limit: int = 100) -> List[Dict[str, Any]]:
        await self.initialize()
        history = await PriceHistory.find(
            PriceHistory.asin == asin
        ).sort(-PriceHistory.timestamp).limit(limit).to_list()
        
        return [item.model_dump() for item in history]
