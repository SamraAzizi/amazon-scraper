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
        return result[0] if result else None
    except Exception as e:
        import traceback
        raise RuntimeError(f"Failed to send query event: {str(e)}\n{traceback.format_exc()}") from e

if prompt := st.chat_input("Ask about products, prices, trends, etc."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching products and generating answer..."):
                try:
                    event_id = run_async(send_query_event(prompt.strip(), top_k=10))
                except Exception as e:
                    st.error(f"Failed to send event: {str(e)}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: Failed to send query. {str(e)}"})
                    st.stop()
                
                if not event_id:
                    st.error("Failed to send query to Inngest - no event ID returned")
                    st.session_state.messages.append({"role": "assistant", "content": "Error: Failed to send query to Inngest"})
                    st.stop()
                
                try:
                    output = wait_for_run_output(event_id, timeout_s=120.0)
                except TimeoutError as e:
                    st.error(f"Query timed out after 120 seconds. Event ID: {event_id}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: Query timed out. Event ID: {event_id}"})
                    st.stop()
                except Exception as e:
                    st.error(f"Error waiting for response: {str(e)}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
                    st.stop()
                
                if not output:
                    st.error("No output received from Inngest function")
                    st.session_state.messages.append({"role": "assistant", "content": "Error: No output received from query function"})
                    st.stop()
                
                answer = output.get("answer", "I couldn't generate a response.")
                sources = output.get("sources", [])
                products_found = output.get("products_found", 0)
                
                st.markdown(answer)
                
                if sources:
                    with st.expander(f"Sources ({products_found} products found)"):
                        for source in sources[:10]:
                            st.write(f"- {source}")
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n\nFull error: {traceback.format_exc()}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})

st.divider()

tab1, tab2 = st.tabs(["All Products", "Price Comparison"])

with tab1:
    st.subheader("Database Products")
    
    db = SyncDatabase()
    products = db.get_all_products()
    
    if products:
        st.write(f"Total products in database: {len(products)}")
        
        items_per_page = 10
        total_pages = (len(products) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="products_page") - 1
        else:
            page = 0
        
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(products))
        
        for p in products[start_idx:end_idx]:
            with st.container(border=True):
                cols = st.columns([1, 3])
                if p.get("images"):
                    try:
                        img_url = p["images"][0] if isinstance(p["images"], list) and len(p["images"]) > 0 else p["images"]
                        if isinstance(img_url, str) and img_url.startswith(("http://", "https://")):
                            cols[0].image(img_url, width=150, use_container_width=False)
                        else:
                            cols[0].write("No image")
                    except Exception as e:
                        cols[0].write("Image unavailable")
                
                with cols[1]:
                    st.write(f"**{p.get('title', p.get('asin'))}**")
                    st.write(f"ASIN: {p.get('asin')}")
                    if p.get("price_display"):
                        st.write(f"Price: {p.get('price_display')}")
                    elif p.get("price") is not None:
                        currency_symbol = p.get("currency_symbol", p.get("currency", ""))
                        st.write(f"Price: {currency_symbol}{p.get('price')}")
                    if p.get("rating"):
                        st.write(f"Rating: {p.get('rating')}")
                    if p.get("brand"):
                        st.write(f"Brand: {p.get('brand')}")
                    if p.get("scraped_url") or p.get("url"):
                        scraped_url = p.get("scraped_url") or p.get("url")
                        st.write(f"[View Product on Amazon]({scraped_url})")
                    if p.get("scraped_at"):
                        st.caption(f"Scraped: {p.get('scraped_at')}")
                    st.caption(f"Domain: amazon.{p.get('amazon_domain', 'com')} | Location: {p.get('geo_location', '-')}")
    else:
        st.info("No products in database yet. Scrape a product to get started.")

with tab2:
    st.subheader("Price Comparison by ASIN")
    
    db = SyncDatabase()
    grouped_products = db.get_products_grouped_by_asin()
    
    if grouped_products:
        asins_with_multiple = {asin: products for asin, products in grouped_products.items() if len(products) > 1}
        
        if asins_with_multiple:
            st.write(f"Found {len(asins_with_multiple)} products with multiple country listings")
            
            selected_asin = st.selectbox(
                "Select ASIN to compare",
                options=list(asins_with_multiple.keys()),
                format_func=lambda x: f"{x} ({len(asins_with_multiple[x])} countries)"
            )
            
            if selected_asin:
                products = asins_with_multiple[selected_asin]
                
                st.write(f"**{products[0].get('title', selected_asin)}**")
                st.write(f"ASIN: {selected_asin}")
                
                if products[0].get("images"):
                    try:
                        img_url = products[0]["images"][0] if isinstance(products[0]["images"], list) and len(products[0]["images"]) > 0 else products[0]["images"]
                        if isinstance(img_url, str) and img_url.startswith(("http://", "https://")):
                            st.image(img_url, width=300)
                    except:
                        pass
                
                st.divider()
                
                comparison_data = []
                for p in products:
                    comparison_data.append({
                        "Country": p.get("geo_location", "Unknown"),
                        "Domain": f"amazon.{p.get('amazon_domain', 'com')}",
                        "Price": p.get("price_display", f"{p.get('currency_symbol', p.get('currency', ''))}{p.get('price', 'N/A')}") if (p.get("price_display") or p.get("price") is not None) else "N/A",
                        "Currency": p.get("currency", ""),
                        "Price Value": p.get("price"),
                        "Rating": p.get("rating", "N/A"),
                        "Stock": p.get("stock", "Unknown"),
                        "Scraped": str(p.get("scraped_at", "Unknown"))[:10] if p.get("scraped_at") else "Unknown",
                        "URL": p.get("scraped_url") or p.get("url", "")
                    })
                
                df = pd.DataFrame(comparison_data)
                df = df.sort_values("Price Value", na_position="last")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.subheader("Price Chart")
                price_df = df[df["Price Value"].notna()].copy()
                if not price_df.empty:
                    price_df = price_df.sort_values("Price Value")
                    st.bar_chart(price_df.set_index("Country")["Price Value"])
                
                st.subheader("Individual Listings")
                for p in products:
                    with st.container(border=True):
                        cols = st.columns([1, 2])
                        if p.get("images"):
                            try:
                                img_url = p["images"][0] if isinstance(p["images"], list) and len(p["images"]) > 0 else p["images"]
                                if isinstance(img_url, str) and img_url.startswith(("http://", "https://")):
                                    cols[0].image(img_url, width=150)
                            except:
                                cols[0].write("No image")
                        
                        with cols[1]:
                            st.write(f"**{p.get('geo_location', 'Unknown')} - amazon.{p.get('amazon_domain', 'com')}**")
                            if p.get("price_display"):
                                st.metric("Price", p.get("price_display"))
                            elif p.get("price") is not None:
                                currency_symbol = p.get("currency_symbol", p.get("currency", ""))
                                st.metric("Price", f"{currency_symbol}{p.get('price')}")
                            if p.get("rating"):
                                st.write(f"Rating: {p.get('rating')}")
                            if p.get("stock"):
                                st.write(f"Stock: {p.get('stock')}")
                            if p.get("scraped_url") or p.get("url"):
                                scraped_url = p.get("scraped_url") or p.get("url")
                                st.write(f"[View on Amazon]({scraped_url})")
                            if p.get("scraped_at"):
                                st.caption(f"Scraped: {p.get('scraped_at')}")
        else:
            st.info("No products with multiple country listings found. Scrape the same ASIN in different countries to see price comparisons.")
    else:
        st.info("No products in database yet. Scrape a product to get started.")