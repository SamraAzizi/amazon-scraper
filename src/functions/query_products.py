import os
import inngest
from datetime import datetime
from pydantic import BaseModel
from typing import List
from ..database import Database
from ..vector_store import QdrantStore
from ..embeddings import get_embeddings
from openai import OpenAI


class VectorSearchResult(BaseModel):
    contexts: List[str]
    sources: List[str]
    products: List[dict]


def create_query_products_function(inngest_client):
    @inngest_client.create_function(
        fn_id="query_products",
        trigger=inngest.TriggerEvent(event="amazon/query_products"),
    )
    async def query_products_function(ctx: inngest.Context):
        def _vector_search(question: str, top_k: int = 10) -> VectorSearchResult:
            embeddings = get_embeddings()
            vector_store = QdrantStore()
            
            query_vector = embeddings.embed_query(question)
            results = vector_store.search(query_vector, top_k)
            
            return VectorSearchResult(
                contexts=results.get("contexts", []),
                sources=results.get("sources", []),
                products=results.get("products", [])
            )
        
        async def _get_product_details(asin: str):
            db = Database()
            products = await db.search_products({"asin": asin})
            return products
        
        async def _get_price_history(asin: str, limit: int = 20):
            db = Database()
            history = await db.get_price_history(asin, limit)
            return history
        
        question = ctx.event.data["question"]
        top_k = int(ctx.event.data.get("top_k", 10))
        
        search_result = await ctx.step.run("vector-search", lambda: _vector_search(question, top_k), output_type=VectorSearchResult)
        
        if not search_result.contexts and not search_result.products:
            context_block = "No products found in the database matching your query."
        else:
            context_block = "\n\n".join([f"Product {i+1}:\n{ctx}" for i, ctx in enumerate(search_result.contexts)])
        
        if search_result.sources:
            unique_asins = list(set(search_result.sources))
            all_products = []
            price_histories = {}
            
            for asin in unique_asins[:5]:
                products = await _get_product_details(asin)
                all_products.extend(products)
                
                history = await _get_price_history(asin, 10)
                if history:
                    price_histories[asin] = history
        
            products_summary = []
            for p in all_products:
                summary = f"ASIN: {p.get('asin')}, Title: {p.get('title', 'N/A')}, Price: {p.get('price_display', 'N/A')}, Location: {p.get('geo_location')}, Domain: amazon.{p.get('amazon_domain', 'com')}, Rating: {p.get('rating', 'N/A')}"
                products_summary.append(summary)
            
            additional_context = f"\n\nDetailed Product Information:\n" + "\n".join(products_summary)
            
            if price_histories:
                history_context = "\n\nPrice History:\n"
                for asin, history in price_histories.items():
                    history_context += f"\n{asin}:\n"
                    for h in history[:5]:
                        timestamp = h.get('timestamp', '')
                        if isinstance(timestamp, datetime):
                            timestamp = timestamp.isoformat()
                        elif hasattr(timestamp, 'isoformat'):
                            timestamp = timestamp.isoformat()
                        history_context += f"  {timestamp}: {h.get('currency', '')} {h.get('price', 'N/A')}\n"
                additional_context += history_context
        else:
            additional_context = ""