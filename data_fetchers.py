"""
Data fetchers for the two sources:
- CoinDCX public API for crypto (free, no auth needed)
- Yahoo Finance (via yfinance) for Indian stocks (free, ~15min delayed for some exchanges)
"""

import requests
import time
from typing import List, Dict, Optional


COINDCX_BASE = "https://public.coindcx.com"


def fetch_coindcx_candles(pair: str, interval: str = "15m", limit: int = 200) -> List[Dict]:
    """
    pair example: 'B-BTC_USDT'
    interval: '1m','5m','15m','30m','1h','2h','4h','6h','8h','1d' etc (CoinDCX format)
    Returns list of candles oldest->newest: [{'open','high','low','close','volume','time'}, ...]
    CoinDCX returns newest-first, so we reverse.
    """
    url = f"{COINDCX_BASE}/market_data/candles"
    params = {"pair": pair, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    data = list(reversed(data))  # oldest first
    return data


def fetch_yahoo_candles(ticker: str, interval: str = "15m", period: str = "5d") -> List[Dict]:
    """
    ticker example: 'RELIANCE.NS' (NSE stock), '^NSEI' (Nifty 50 index)
    interval: yfinance format - '15m','30m','1h','1d' etc
    period: how far back - yfinance only allows ~60 days of intraday history at 15m interval
    Returns list of candles oldest->newest: [{'open','high','low','close','volume','time'}, ...]
    """
    import yfinance as yf

    df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return []

    # yfinance sometimes returns multi-index columns when multiple tickers requested;
    # since we request one ticker at a time, flatten if needed.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)

    candles = []
    for ts, row in df.iterrows():
        candles.append({
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row.get("Volume", 0) or 0),
            "time": int(ts.timestamp() * 1000),
        })
    return candles
