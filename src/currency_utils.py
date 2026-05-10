from typing import Dict


DOMAIN_MAP: Dict[str, str] = {
    "us": "com",
    "uk": "co.uk",
    "ca": "ca",
    "de": "de",
    "fr": "fr",
    "it": "it",
    "es": "es",
    "ae": "ae",
    "au": "com.au",
    "jp": "co.jp"
}

CURRENCY_MAP: Dict[str, str] = {
    "us": "USD",
    "uk": "GBP",
    "ca": "CAD",
    "de": "EUR",
    "fr": "EUR",
    "it": "EUR",
    "es": "EUR",
    "ae": "AED",
    "au": "AUD",
    "jp": "JPY",
    "in": "INR",
    "mx": "MXN",
    "br": "BRL",
    "sg": "SGD",
}

CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "JPY": "¥",
    "AED": "AED",
    "INR": "₹",
    "MXN": "MX$",
    "BRL": "R$",
    "SGD": "S$",
}

CURRENCY_PATTERNS: Dict[str, list] = {
    "CAD": ["C$", "CAD", "CA$", "CDN$", "CAN$", "CDN"],
    "AUD": ["A$", "AUD", "AU$"],
    "MXN": ["MX$", "MXN", "PESO"],
    "BRL": ["R$", "BRL", "REAL"],
    "SGD": ["S$", "SGD"],
    "AED": ["AED", "د.إ", "DH", "DHS", "درهم"],
    "USD": ["$", "USD", "US$"],
    "EUR": ["€", "EUR", "EURO"],
    "GBP": ["£", "GBP"],
    "JPY": ["¥", "JPY", "YEN"],
    "INR": ["₹", "INR", "RS", "RUPEES"],
}


def get_amazon_domain(country_code: str) -> str:
    return DOMAIN_MAP.get(country_code.lower(), "com")


def get_country_currency(country_code: str) -> str:
    return CURRENCY_MAP.get(country_code.lower(), "USD")


def get_currency_symbol(currency_code: str) -> str:
    return CURRENCY_SYMBOLS.get(currency_code, "$")


def extract_currency(price_text: str, country_code: str = None) -> str:
    if not price_text:
        return get_country_currency(country_code) if country_code else "USD"
    
    price_text_upper = price_text.upper()
    
    for currency_code, patterns in CURRENCY_PATTERNS.items():
        for pattern in patterns:
            if pattern in price_text_upper:
                return currency_code
    
    return get_country_currency(country_code) if country_code else "USD"