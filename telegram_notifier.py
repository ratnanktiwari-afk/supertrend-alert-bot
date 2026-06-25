"""
Telegram notifier. Uses the Bot API directly via HTTP (no extra library needed).

Setup (one-time, manual):
1. Talk to @BotFather on Telegram, /newbot, get your TOKEN.
2. Send any message (e.g. "hi") to your new bot from your own Telegram account.
3. Run `python get_chat_id.py` (included) to auto-discover your chat_id from that message.
4. Put TOKEN and CHAT_ID into config.py
"""

import requests


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram] Failed to send message: {e}")
        return False


def format_event_message(symbol: str, timeframe: str, event: dict) -> str:
    etype = event["type"]

    if etype == "BUY_SIGNAL":
        return f"🟢 <b>{symbol}</b> ({timeframe})\nSupertrend BUY signal\nPrice: {event['price']:.4f}"
    if etype == "SELL_SIGNAL":
        return f"🔴 <b>{symbol}</b> ({timeframe})\nSupertrend SELL signal\nPrice: {event['price']:.4f}"
    if etype == "BUY_ENTRY":
        return (f"✅ <b>{symbol} BUY ENTRY</b> ({timeframe})\n"
                f"Entry: {event['price']:.4f}\nSL: {event['sl']:.4f}\nTarget: {event['target']:.4f}")
    if etype == "SELL_ENTRY":
        return (f"✅ <b>{symbol} SELL ENTRY</b> ({timeframe})\n"
                f"Entry: {event['price']:.4f}\nSL: {event['sl']:.4f}\nTarget: {event['target']:.4f}")
    if etype == "TARGET_PARTIAL":
        return f"🎯 <b>{symbol} TARGET HIT</b> ({timeframe})\n40% Booked, trailing SL on remaining 60%\nPrice: {event['price']:.4f}"
    if etype == "TRAIL_SL_HIT":
        return f"🟣 <b>{symbol} TRAILING SL HIT</b> ({timeframe})\nRemaining position closed\nPrice: {event['price']:.4f}"
    if etype == "SL_HIT":
        return f"❌ <b>{symbol} SL HIT</b> ({timeframe})\nPrice: {event['price']:.4f}"
    if etype == "EXIT":
        return f"⚠️ <b>{symbol} EXIT</b> ({timeframe}) - Opposite signal\nPrice: {event['price']:.4f}"

    return f"{symbol} ({timeframe}): {event}"
