from typing import Dict, Any


def is_valid_product(product_data: Dict[str, Any]) -> bool:
    if not product_data.get("asin"):
        return False
    
    has_title = bool(product_data.get("title") and product_data.get("title").strip())
    has_price = product_data.get("price") is not None or bool(product_data.get("price_display"))
    has_brand = bool(product_data.get("brand") and product_data.get("brand").strip())
    
    return has_title or (has_price and has_brand)