import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"
COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
