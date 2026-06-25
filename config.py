"""
Edit this file to set your bot token, chat id, and the symbols you want to track.
"""

import os

# ===== TELEGRAM =====
# These are read from environment variables (set as GitHub Secrets when running
# in GitHub Actions). For local testing, you can temporarily hardcode them here,
# but NEVER commit real tokens to a public repo.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PUT_YOUR_CHAT_ID_HERE")

# ===== TIMEFRAME =====
TIMEFRAME = "15m"          # used for both crypto (CoinDCX format) and stocks (yfinance format)

# ===== SUPERTREND SETTINGS (must match your Pine indicator) =====
ST_PERIOD = 21
ST_FACTOR = 0.8

# ===== HOW OFTEN TO CHECK FOR NEW CANDLES (seconds) =====
POLL_INTERVAL_SECONDS = 60     # check every 1 minute if a new 15m candle has closed

# ===== SYMBOLS =====
# type: "crypto" -> uses CoinDCX pair format, e.g. "B-BTC_USDT"
# type: "stock"  -> uses Yahoo Finance ticker format, e.g. "RELIANCE.NS" or "^NSEI" for Nifty 50
SYMBOLS = [
    {"type": "crypto", "symbol": "B-BTC_USDT", "display": "BTC/USDT"},
    {"type": "stock",  "symbol": "^NSEI",      "display": "NIFTY 50"},
    # add more here later, e.g.:
    # {"type": "crypto", "symbol": "B-ETH_USDT", "display": "ETH/USDT"},
    # {"type": "stock",  "symbol": "RELIANCE.NS", "display": "RELIANCE"},
]
