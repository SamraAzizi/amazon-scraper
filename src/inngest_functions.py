import logging
import os
import inngest
import inngest.fast_api
from fastapi import FastAPI
from dotenv import load_dotenv
from .functions import create_scrape_product_function, create_query_products_function

load_dotenv()

inngest_api_base = os.getenv("INNGEST_API_BASE_URL", os.getenv("INNGEST_API_BASE", "http://inngest:8288"))

inngest_client = inngest.Inngest(
    app_id="amazon_price_agent",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    api_base_url=inngest_api_base,
    serializer=inngest.PydanticSerializer(),
)

scrape_product_function = create_scrape_product_function(inngest_client)
query_products_function = create_query_products_function(inngest_client)

app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [scrape_product_function, query_products_function])