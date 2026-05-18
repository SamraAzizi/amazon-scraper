from langchain_core.tools import tool
from typing import Dict, Any
from .database import SyncDatabase
from .scraper import AmazonScraper
from .vector_store import QdrantStore
from .embeddings import get_embeddings


@tool
def scrape_product(asin: str, country_code: str) -> Dict[str, Any]:
    scraper = AmazonScraper()
    return scraper.scrape_product(asin, country_code)


@tool
def get_product(asin: str, geo_location: str = None) -> Dict[str, Any]:
    db = SyncDatabase()
    if geo_location:
        products = db.search_products({"asin": asin, "geo_location": geo_location.upper()})
        return products[0] if products else {"error": f"Product {asin} not found for {geo_location}"}
    else:
        products = db.search_products({"asin": asin})
        return products[0] if products else {"error": f"Product {asin} not found in database"}


@tool
def get_price_history(asin: str, limit: int = 100):
    db = SyncDatabase()
    return db.get_price_history(asin, limit)


@tool
def search_products(criteria: Dict[str, Any]):
    db = SyncDatabase()
    return db.search_products(criteria)


@tool
def vector_search(query: str, top_k: int = 10):
    try:
        embeddings = get_embeddings()
        vector_store = QdrantStore()
        
        query_vector = embeddings.embed_query(query)
        results = vector_store.search(query_vector, top_k)
        
        if not results.get("products") and not results.get("contexts"):
            return {
                "products": [],
                "contexts": [],
                "sources": [],
                "message": f"No products found matching: {query}"
            }
        
        return results
    except Exception as e:
        return {
            "products": [],
            "contexts": [],
            "sources": [],
            "error": f"Vector search failed: {str(e)}"
        }