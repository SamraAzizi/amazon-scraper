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

    async def search_products(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        await self.initialize()
        
        query = {}
        for key, value in criteria.items():
            query[key] = value
        
        products = await Product.find(query).to_list()
        return [product.model_dump() for product in products]

    async def get_all_products(self) -> List[Dict[str, Any]]:
        await self.initialize()
        products = await Product.find_all().to_list()
        return [product.model_dump() for product in products]

    async def get_products_by_asin(self, asin: str) -> List[Dict[str, Any]]:
        await self.initialize()
        products = await Product.find(Product.asin == asin).to_list()
        return [product.model_dump() for product in products]

    async def get_products_grouped_by_asin(self) -> Dict[str, List[Dict[str, Any]]]:
        await self.initialize()
        products = await Product.find_all().to_list()
        grouped = {}
        for product in products:
            asin = product.asin
            if asin not in grouped:
                grouped[asin] = []
            grouped[asin].append(product.model_dump())
        return grouped

    async def delete_all_products(self) -> int:
        await self.initialize()
        result = await Product.delete_all()
        return result.deleted_count

    async def delete_all_price_history(self) -> int:
        await self.initialize()
        result = await PriceHistory.delete_all()
        return result.deleted_count


class SyncDatabase:
    _loop = None
    _loop_thread = None
    _lock = None
    
    def __init__(self):
        self.db = Database()
        if SyncDatabase._lock is None:
            import threading
            SyncDatabase._lock = threading.Lock()
        
        self._ensure_loop()

    def _ensure_loop(self):
        if SyncDatabase._loop is None or SyncDatabase._loop.is_closed():
            import asyncio
            import threading
            
            def run_loop(loop):
                asyncio.set_event_loop(loop)
                loop.run_forever()
            
            SyncDatabase._loop = asyncio.new_event_loop()
            SyncDatabase._loop_thread = threading.Thread(
                target=run_loop,
                args=(SyncDatabase._loop,),
                daemon=True
            )
            SyncDatabase._loop_thread.start()

    def _run_async(self, coro):
        import asyncio
        import concurrent.futures
        
        self._ensure_loop()
        
        future = asyncio.run_coroutine_threadsafe(coro, SyncDatabase._loop)
        return future.result(timeout=30)

    def insert_or_update_product(self, product_data: Dict[str, Any]) -> str:
        return self._run_async(self.db.insert_or_update_product(product_data))

    def get_product(self, asin: str, geo_location: str = None) -> Optional[Dict[str, Any]]:
        return self._run_async(self.db.get_product(asin, geo_location))

    def get_price_history(self, asin: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._run_async(self.db.get_price_history(asin, limit))

    def search_products(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._run_async(self.db.search_products(criteria))

    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._run_async(self.db.get_all_products())

    def get_products_by_asin(self, asin: str) -> List[Dict[str, Any]]:
        return self._run_async(self.db.get_products_by_asin(asin))

    def get_products_grouped_by_asin(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._run_async(self.db.get_products_grouped_by_asin())

    def delete_all_products(self) -> int:
        return self._run_async(self.db.delete_all_products())

    def delete_all_price_history(self) -> int:
        return self._run_async(self.db.delete_all_price_history())