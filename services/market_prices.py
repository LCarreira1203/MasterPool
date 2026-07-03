import requests

from config import BINANCE_PRICE_URL, BINANCE_24H_URL, COINGECKO_SIMPLE_PRICE_URL
from services.crypto_search import search_crypto


STABLES = {"USDT", "USDC", "USD", "BUSD", "DAI"}

COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "USDC": "usd-coin",
    "USDT": "tether",
    "BNB": "binancecoin",
    "JUP": "jupiter-exchange-solana",
    "BONK": "bonk",
    "RAY": "raydium",
    "ORCA": "orca",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AVAX": "avalanche-2",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "PEPE": "pepe",
}


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_usd_brl():
    try:
        response = requests.get(
            BINANCE_PRICE_URL,
            params={"symbol": "USDTBRL"},
            timeout=10,
        )
        response.raise_for_status()
        price = safe_float(response.json().get("price"))
        if price:
            return price
    except requests.RequestException:
        pass

    try:
        response = requests.get(
            COINGECKO_SIMPLE_PRICE_URL,
            params={
                "ids": "tether",
                "vs_currencies": "brl",
            },
            timeout=10,
        )
        response.raise_for_status()
        price = safe_float(response.json().get("tether", {}).get("brl"))
        if price:
            return price
    except requests.RequestException:
        pass

    return None


def get_binance_price(symbol):
    symbol = symbol.upper().strip()

    if symbol in {"USDT", "USDC", "USD"}:
        return 1.0, 0

    for quote in ["USDT", "USDC", "BUSD"]:
        pair_symbol = f"{symbol}{quote}"

        try:
            price_response = requests.get(
                BINANCE_PRICE_URL,
                params={"symbol": pair_symbol},
                timeout=10,
            )

            if price_response.status_code != 200:
                continue

            price_response.raise_for_status()
            price = safe_float(price_response.json().get("price"))

            if price is None:
                continue

            change_24h = 0
            try:
                change_response = requests.get(
                    BINANCE_24H_URL,
                    params={"symbol": pair_symbol},
                    timeout=10,
                )
                if change_response.status_code == 200:
                    change_24h = safe_float(
                        change_response.json().get("priceChangePercent"),
                        0,
                    )
            except requests.RequestException:
                change_24h = 0

            return price, change_24h

        except requests.RequestException:
            continue

    return None, None


def get_coingecko_price(symbol):
    symbol = symbol.upper().strip()
    coin_id = COINGECKO_IDS.get(symbol)

    if not coin_id:
        return None, None

    try:
        response = requests.get(
            COINGECKO_SIMPLE_PRICE_URL,
            params={
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get(coin_id, {})

        price = safe_float(data.get("usd"))
        change_24h = safe_float(data.get("usd_24h_change"), 0)

        if price is None:
            return None, None

        return price, change_24h

    except requests.RequestException:
        return None, None


def get_dexscreener_price(symbol):
    pairs, error = search_crypto(symbol)

    if error or not pairs:
        return None, None

    symbol = symbol.upper().strip()

    for pair in pairs:
        base = pair.get("baseToken", {}).get("symbol", "").upper()
        quote = pair.get("quoteToken", {}).get("symbol", "").upper()

        if base == symbol and quote in STABLES:
            price = safe_float(pair.get("priceUsd"))
            change_24h = safe_float(pair.get("priceChange", {}).get("h24"), 0)

            if price is not None:
                return price, change_24h

    for pair in pairs:
        base = pair.get("baseToken", {}).get("symbol", "").upper()

        if base == symbol:
            price = safe_float(pair.get("priceUsd"))
            change_24h = safe_float(pair.get("priceChange", {}).get("h24"), 0)

            if price is not None:
                return price, change_24h

    return None, None


def get_token_price(symbol):
    symbol = symbol.upper().strip()

    if symbol in {"USD", "USDT", "USDC"}:
        usd_brl = get_usd_brl()
        return {
            "symbol": symbol,
            "price_usd": 1.0,
            "price_brl": usd_brl,
            "change_24h": 0,
            "source": "Stablecoin",
        }

    sources = [
        ("Binance", get_binance_price),
        ("CoinGecko", get_coingecko_price),
        ("DexScreener", get_dexscreener_price),
    ]

    for source_name, source_func in sources:
        price_usd, change_24h = source_func(symbol)

        if price_usd is not None:
            usd_brl = get_usd_brl()
            price_brl = price_usd * usd_brl if usd_brl else None

            return {
                "symbol": symbol,
                "price_usd": price_usd,
                "price_brl": price_brl,
                "change_24h": change_24h,
                "source": source_name,
            }

    return {
        "symbol": symbol,
        "price_usd": None,
        "price_brl": None,
        "change_24h": None,
        "source": None,
    }


def get_symbols_from_pair(pair):
    parts = [p.strip().upper() for p in pair.split("/") if p.strip()]
    return parts


def get_unique_symbols_from_pools(pools):
    symbols = []

    for pool in pools:
        for symbol in get_symbols_from_pair(pool.get("pair", "")):
            if symbol and symbol not in symbols:
                symbols.append(symbol)

    return symbols
