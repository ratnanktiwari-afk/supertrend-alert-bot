"""
Entry point designed for GitHub Actions (or any cron-style trigger).

Unlike a long-running loop, this script:
1. Loads each symbol's saved state from state.json (if it exists)
2. Fetches latest candles
3. Processes any newly-closed candles through the strategy engine
4. Sends Telegram alerts for any events
5. Saves updated state back to state.json
6. Exits

GitHub Actions runs this on a schedule (e.g. every 15 minutes) and commits
the updated state.json back to the repo so the next run can resume correctly.
"""

import json
import os
import traceback

import config
from strategy_engine import SymbolState, compute_supertrend, process_candle
from data_fetchers import fetch_coindcx_candles, fetch_yahoo_candles
from telegram_notifier import send_telegram_message, format_event_message

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


def load_states():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        raw = json.load(f)
    return {sym: SymbolState.from_dict(d) for sym, d in raw.items()}


def save_states(states):
    raw = {sym: state.to_dict() for sym, state in states.items()}
    with open(STATE_FILE, "w") as f:
        json.dump(raw, f, indent=2)


def fetch_candles_for(sym_cfg):
    if sym_cfg["type"] == "crypto":
        return fetch_coindcx_candles(sym_cfg["symbol"], interval=config.TIMEFRAME, limit=300)
    elif sym_cfg["type"] == "stock":
        return fetch_yahoo_candles(sym_cfg["symbol"], interval=config.TIMEFRAME, period="60d")
    else:
        raise ValueError(f"Unknown symbol type: {sym_cfg['type']}")


def run_once():
    states = load_states()

    for sym_cfg in config.SYMBOLS:
        symbol_key = sym_cfg["symbol"]
        display = sym_cfg.get("display", symbol_key)

        if symbol_key not in states:
            states[symbol_key] = SymbolState(symbol=symbol_key)
        state = states[symbol_key]

        try:
            candles = fetch_candles_for(sym_cfg)
            if not candles or len(candles) < config.ST_PERIOD + 2:
                print(f"[{display}] Not enough candles ({len(candles) if candles else 0}), skipping.")
                continue

            # drop the most recent candle - it's likely still forming/incomplete
            closed_candles = candles[:-1]

            direction = compute_supertrend(closed_candles, period=config.ST_PERIOD, factor=config.ST_FACTOR)

            # only process candles newer than what we've already seen
            start_idx = 0
            if state.last_processed_time is not None:
                start_idx = len(closed_candles)  # default: nothing new
                for i, c in enumerate(closed_candles):
                    if c["time"] > state.last_processed_time:
                        start_idx = i
                        break

            new_count = len(closed_candles) - start_idx
            print(f"[{display}] {new_count} new candle(s) to process.")

            for i in range(start_idx, len(closed_candles)):
                events = process_candle(state, closed_candles[i], direction[i])
                for ev in events:
                    msg = format_event_message(display, config.TIMEFRAME, ev)
                    ok = send_telegram_message(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID, msg)
                    print(f"[{display}] Sent: {ev['type']} (success={ok})")
                state.last_processed_time = closed_candles[i]["time"]

        except Exception as e:
            print(f"[ERROR] {display}: {e}")
            traceback.print_exc()

    save_states(states)


if __name__ == "__main__":
    run_once()
