import inngest
from ..scraper import AmazonScraper
from ..database import Database
from ..vector_store import QdrantStore
from ..embeddings import get_embeddings


def create_scrape_product_function(inngest_client):
    @inngest_client.create_function(
        fn_id="scrape_product",
        trigger=inngest.TriggerEvent(event="amazon/scrape_product"),
    )
    async def scrape_product_function(ctx: inngest.Context):
        asin = ctx.event.data["asin"]
        country_code = ctx.event.data["country_code"]
        
        def _scrape():
            scraper = AmazonScraper()
            try:
                product_data = scraper.scrape_product(asin, country_code)
                return product_data
            except ValueError as e:
                if "empty or invalid" in str(e):
                    return {"skipped": True, "reason": str(e), "asin": asin}
                raise
        
        async def _store(product_data):
            db = Database()
            try:
                await db.insert_or_update_product(product_data)
            except ValueError as e:
                if "empty or invalid" in str(e):
                    return {"skipped": True, "reason": str(e), "asin": product_data.get("asin")}
                raise
            return product_data
        
        def _embed(product_data):
            embeddings = get_embeddings()
            vector_store = QdrantStore()
            
            title = product_data.get('title', '')
            brand = product_data.get('brand', '')
            overview_items = product_data.get('product_overview', [])
            categories = product_data.get('categories', [])
            price_display = product_data.get('price_display', '')
            price = product_data.get('price')
            currency = product_data.get('currency', '')
            currency_symbol = product_data.get('currency_symbol', '')
            rating = product_data.get('rating')
            geo_location = product_data.get('geo_location', '')
            amazon_domain = product_data.get('amazon_domain', '')
            
            overview_text = ' '.join(overview_items) if isinstance(overview_items, list) else str(overview_items)
            categories_text = ' '.join(categories) if isinstance(categories, list) else str(categories)
            
            text_content = f"""
Product: {title}
Brand: {brand}
Price: {price_display or (f"{currency_symbol}{price}" if price else "Not available")}
Currency: {currency}
Rating: {rating if rating else "Not available"}
Location: {geo_location}
Domain: amazon.{amazon_domain}
Categories: {categories_text}
Description: {overview_text}
""".strip()