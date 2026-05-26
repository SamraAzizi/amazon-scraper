import asyncio
import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests
import threading
import pandas as pd
from src.database import SyncDatabase

load_dotenv()

st.set_page_config(page_title="Amazon Price Agent", page_icon="🛒", layout="wide")


_inngest_client = None

def get_inngest_client():
    global _inngest_client
    if _inngest_client is None:
        _inngest_client = inngest.Inngest(app_id="amazon_price_agent", is_production=False)
    return _inngest_client




_async_loop = None
_async_loop_thread = None


def _get_async_loop():
    global _async_loop, _async_loop_thread
    
    if _async_loop is None or _async_loop.is_closed():
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        
        _async_loop = asyncio.new_event_loop()
        _async_loop_thread = threading.Thread(
            target=run_loop,
            args=(_async_loop,),
            daemon=True
        )
        _async_loop_thread.start()
        
        import time
        time.sleep(0.1)
    
    return _async_loop


def run_async(coro):
    loop = _get_async_loop()
    
    if not loop.is_running():
        import time
        time.sleep(0.1)
    
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=60)


def _inngest_api_base():
    return os.getenv("INNGEST_API_BASE_URL", os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288")) + "/v1"


def fetch_runs(event_id: str):
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5):
    import time
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


async def send_scrape_event(asin: str, country_code: str):
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="amazon/scrape_product",
            data={
                "asin": asin,
                "country_code": country_code,
            },
        )
    )
    return result[0] if result else None


st.title("Amazon Price Agent")

col1, col2 = st.columns([1, 1])

with col1:
    asin = st.text_input("ASIN", placeholder="e.g., B08N5WRWNW", key="asin_input")
    country_codes = ["us", "uk", "ca", "de", "fr", "it", "es", "ae", "au", "jp"]
    selected_countries = st.multiselect("Target Countries", country_codes, default=["us"])

with col2:
    if st.button("Scrape Product", type="primary"):
        if asin and selected_countries:
            for country in selected_countries:
                with st.spinner(f"Scraping {asin} for {country}..."):
                    try:
                        event_id = run_async(send_scrape_event(asin, country))
                        if event_id:
                            output = wait_for_run_output(event_id)
                            st.success(f"Scraped {asin} for {country}")
                    except Exception as e:
                        st.error(f"Error scraping {country}: {str(e)}")
        else:
            st.warning("Please enter an ASIN and select at least one country")

st.divider()

st.subheader("Ask Questions About Products")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def send_query_event(question: str, top_k: int = 10):
    try:
        client = get_inngest_client()
        result = await client.send(
            inngest.Event(
                name="amazon/query_products",
                data={
                    "question": question,
                    "top_k": top_k,
                },
            )
        )