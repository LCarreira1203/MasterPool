import requests

from config import COINGECKO_SIMPLE_PRICE_URL


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


def get_coingecko_price(symbol):
    symbol = symbol.upper().strip()

    if symbol in {"USD", "USDT", "USDC"}:
        return {
            "symbol": symbol,
            "price_usd": 1.0,
            "price_brl": None,
            "change_24h": 0,
            "source": "Stablecoin",
            "error": None,
        }

    coin_id = COINGECKO_IDS.get(symbol)

    if not coin_id:
        return {
            "symbol": symbol,
            "price_usd": None,
            "price_brl": None,
            "change_24h": None,
            "source": "CoinGecko",
            "error": f"Não encontrei {symbol} no CoinGecko.",
        }

    try:
        response = requests.get(
            COINGECKO_SIMPLE_PRICE_URL,
            params={
                "ids": coin_id,
                "vs_currencies": "usd,brl",
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json().get(coin_id, {})

        price_usd = safe_float(data.get("usd"))
        price_brl = safe_float(data.get("brl"))
        change_24h = safe_float(data.get("usd_24h_change"), 0)

        if price_usd is None:
            return {
                "symbol": symbol,
                "price_usd": None,
                "price_brl": None,
                "change_24h": None,
                "source": "CoinGecko",
                "error": f"CoinGecko não retornou preço para {symbol}.",
            }

        return {
            "symbol": symbol,
            "price_usd": price_usd,
            "price_brl": price_brl,
            "change_24h": change_24h,
            "source": "CoinGecko",
            "error": None,
        }

    except requests.RequestException:
        return {
            "symbol": symbol,
            "price_usd": None,
            "price_brl": None,
            "change_24h": None,
            "source": "CoinGecko",
            "error": f"Falha ao consultar {symbol} no CoinGecko.",
        }


def get_token_price(symbol):
    """
    Fonte única de preço do MasterPool.

    Usa CoinGecko como fonte principal e remove DexScreener/Binance,
    evitando preço torto ou bloqueio por região no Render.
    """
    return get_coingecko_price(symbol)


def get_symbols_from_pair(pair):
    parts = [p.strip().upper() for p in pair.split("/") if p.strip()]
    return parts


def get_unique_symbols_from_pools(pools):
    symbols = []

    for pool in pools:
        symbol = pool.get("symbol")

        if symbol:
            symbol = symbol.upper().strip()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
            continue

        for item in get_symbols_from_pair(pool.get("pair", "")):
            if item and item not in STABLES and item not in symbols:
                symbols.append(item)

    return symbols
