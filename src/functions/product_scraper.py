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
            
            vector_id = f"{asin}_{geo_location}"
            vector = embeddings.embed_query(text_content)
            
            vector_store.upsert(
                ids=[vector_id],
                vectors=[vector],
                payloads=[{
                    "asin": asin,
                    "geo_location": geo_location,
                    "text": text_content,
                    "title": title,
                    "brand": brand,
                    "price": price,
                    "price_display": price_display,
                    "currency": currency,
                    "currency_symbol": currency_symbol,
                    "rating": rating,
                    "categories": categories,
                    "amazon_domain": amazon_domain,
                    "url": product_data.get("url"),
                    "scraped_url": product_data.get("scraped_url")
                }]
            )
            return product_data
        
        product_data = await ctx.step.run("scrape", lambda: _scrape())
        
        if product_data.get("skipped"):
            return {"asin": asin, "status": "skipped", "reason": product_data.get("reason")}
        
        stored = await _store(product_data)
        
        if stored.get("skipped"):
            return {"asin": asin, "status": "skipped", "reason": stored.get("reason")}
        
        if stored.get("title") or (stored.get("price") and stored.get("brand")):
            embedded = await ctx.step.run("embed", lambda: _embed(stored))
            return {"asin": asin, "status": "completed", "product": embedded}
        else:
            return {"asin": asin, "status": "skipped", "reason": "Product missing required fields for embedding"}
    
    return scrape_product_function