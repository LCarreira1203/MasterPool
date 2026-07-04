import requests

from config import BINANCE_PRICE_URL, BINANCE_24H_URL


STABLES = {"USDT", "USDC", "USD", "BUSD", "DAI"}


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_usd_brl():
    """
    Busca cotação USDT/BRL na Binance.
    """
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

    return None


def get_binance_price(symbol):
    """
    Fonte única do MasterPool.
    Busca somente na Binance, nesta ordem:
    TOKENUSDT, TOKENUSDC, TOKENBUSD.
    """
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


def get_token_price(symbol):
    """
    Retorna preço somente pela Binance.
    Se a Binance não encontrar, retorna erro controlado.
    Nunca usa DexScreener nesta versão.
    """
    symbol = symbol.upper().strip()

    price_usd, change_24h = get_binance_price(symbol)

    if price_usd is None:
        return {
            "symbol": symbol,
            "price_usd": None,
            "price_brl": None,
            "change_24h": None,
            "source": "Binance",
            "error": f"Não encontrei {symbol} na Binance. Confira o símbolo ou use outro token.",
        }

    usd_brl = get_usd_brl()
    price_brl = price_usd * usd_brl if usd_brl else None

    return {
        "symbol": symbol,
        "price_usd": price_usd,
        "price_brl": price_brl,
        "change_24h": change_24h,
        "source": "Binance",
        "error": None,
    }


def get_symbols_from_pair(pair):
    return [p.strip().upper() for p in pair.split("/") if p.strip()]


def get_unique_symbols_from_pools(pools):
    symbols = []

    for pool in pools:
        symbol = pool.get("symbol")
        if symbol:
            symbol = symbol.upper().strip()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
            continue

        for symbol in get_symbols_from_pair(pool.get("pair", "")):
            if symbol and symbol not in STABLES and symbol not in symbols:
                symbols.append(symbol)

    return symbols
