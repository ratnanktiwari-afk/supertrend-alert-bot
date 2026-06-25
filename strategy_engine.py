"""
Strategy engine - mirrors the Pine Script logic exactly:
- Supertrend(21, 0.8) for BUY/SELL signal
- Breakout entry: on signal, track signal-candle high/low as breakout level.
  When price breaks that level, ENTRY fires at the NEXT candle's open.
- SL = signal candle's opposite extreme. Target = 1:1 RR.
- On target hit: book 40%, switch remaining 60% into trailing-SL mode
  (trailing SL = each new candle's low for BUY / high for SELL, only moves favorably).
- Opposite signal while in a trade => force EXIT.
- Opposite signal while a breakout is pending (not yet entered) => cancel pending setup.

This module is intentionally stateful per-symbol: call process_candle() once per
new CLOSED candle, in chronological order, and it returns a list of events
(dicts) that occurred on that candle - these get turned into Telegram alerts
by the caller.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


def compute_supertrend(candles: List[Dict[str, float]], period: int = 21, factor: float = 0.8):
    """
    candles: list of dicts with 'high','low','close' in chronological order (oldest first).
    Returns parallel list of direction values: -1 (uptrend/BUY regime) or 1 (downtrend/SELL regime).
    Standard Supertrend algorithm (same as Pine's ta.supertrend).
    """
    n = len(candles)
    if n == 0:
        return []

    # ATR (Wilder's smoothing, matches Pine's ta.atr used internally by ta.supertrend)
    trs = [0.0] * n
    for i in range(n):
        if i == 0:
            trs[i] = candles[i]['high'] - candles[i]['low']
        else:
            h, l, pc = candles[i]['high'], candles[i]['low'], candles[i - 1]['close']
            trs[i] = max(h - l, abs(h - pc), abs(l - pc))

    atr = [0.0] * n
    for i in range(n):
        if i == 0:
            atr[i] = trs[i]
        else:
            atr[i] = (atr[i - 1] * (period - 1) + trs[i]) / period

    upper_band = [0.0] * n
    lower_band = [0.0] * n
    direction = [0] * n
    supertrend = [0.0] * n

    for i in range(n):
        hl2 = (candles[i]['high'] + candles[i]['low']) / 2
        basic_upper = hl2 + factor * atr[i]
        basic_lower = hl2 - factor * atr[i]

        if i == 0:
            upper_band[i] = basic_upper
            lower_band[i] = basic_lower
            direction[i] = -1
            supertrend[i] = lower_band[i]
            continue

        prev_close = candles[i - 1]['close']

        upper_band[i] = basic_upper if (basic_upper < upper_band[i - 1] or prev_close > upper_band[i - 1]) else upper_band[i - 1]
        lower_band[i] = basic_lower if (basic_lower > lower_band[i - 1] or prev_close < lower_band[i - 1]) else lower_band[i - 1]

        close = candles[i]['close']
        if direction[i - 1] == -1:
            direction[i] = 1 if close < lower_band[i] else -1
        else:
            direction[i] = -1 if close > upper_band[i] else 1

        supertrend[i] = lower_band[i] if direction[i] == -1 else upper_band[i]

    return direction


@dataclass
class SymbolState:
    """Per-symbol persistent state, mirrors the Pine `var` variables."""
    symbol: str

    # pending breakout setup
    pending_type: Optional[str] = None          # "BUY" or "SELL"
    pending_breakout_level: Optional[float] = None
    pending_sl: Optional[float] = None
    breakout_done: bool = False
    pending_entry_next_bar: bool = False

    # active trade
    in_trade: bool = False
    in_trailing_mode: bool = False
    trade_type: Optional[str] = None
    entry_price: Optional[float] = None
    sl_price: Optional[float] = None
    target_price: Optional[float] = None

    # for direction tracking (need previous direction to detect signal change)
    prev_direction: Optional[int] = None

    # outcome history for win-rate stats: list of ("SL"/"TARGET", timestamp_ms)
    outcomes: List[tuple] = field(default_factory=list)

    # last candle time we've already processed - lets us resume correctly across runs
    last_processed_time: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["outcomes"] = [list(o) for o in self.outcomes]  # tuples -> lists for JSON
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SymbolState":
        d = dict(d)
        d["outcomes"] = [tuple(o) for o in d.get("outcomes", [])]
        return cls(**d)


def process_candle(state: SymbolState, candle: Dict[str, Any], direction: int) -> List[Dict[str, Any]]:
    """
    candle: dict with 'open','high','low','close','time' (ms epoch) for the CLOSED candle.
    direction: supertrend direction value for this candle (-1 or 1).
    Returns a list of event dicts, e.g.:
      {"type": "BUY_ENTRY", "price": ..., "sl": ..., "target": ...}
      {"type": "SELL_ENTRY", ...}
      {"type": "TARGET_PARTIAL", ...}
      {"type": "TRAIL_SL_HIT", ...}
      {"type": "SL_HIT", ...}
      {"type": "EXIT", ...}
    """
    events = []
    o, h, l, c, t = candle['open'], candle['high'], candle['low'], candle['close'], candle['time']

    buy_signal = state.prev_direction is not None and state.prev_direction != direction and direction == -1
    sell_signal = state.prev_direction is not None and state.prev_direction != direction and direction == 1

    # ===== STEP 1: new signal -> set/replace pending setup, cancel old pending =====
    if buy_signal:
        state.pending_breakout_level = h
        state.pending_sl = l
        state.pending_type = "BUY"
        state.breakout_done = False
        state.pending_entry_next_bar = False
        events.append({"type": "BUY_SIGNAL", "price": c})

    if sell_signal:
        state.pending_breakout_level = l
        state.pending_sl = h
        state.pending_type = "SELL"
        state.breakout_done = False
        state.pending_entry_next_bar = False
        events.append({"type": "SELL_SIGNAL", "price": c})

    # ===== STEP 2: opposite signal while in a trade -> force exit flag =====
    exit_signal_now = False
    if state.in_trade:
        if (state.trade_type == "BUY" and sell_signal) or (state.trade_type == "SELL" and buy_signal):
            exit_signal_now = True

    # ===== STEP 3/4: fire entry on the bar AFTER breakout (at this bar's open) =====
    fire_entry_this_bar = False
    if not state.in_trade and state.pending_entry_next_bar:
        fire_entry_this_bar = True
        state.in_trade = True
        state.trade_type = state.pending_type
        state.entry_price = o
        state.sl_price = state.pending_sl
        risk = abs(state.entry_price - state.sl_price)
        state.target_price = state.entry_price + risk if state.trade_type == "BUY" else state.entry_price - risk

        state.pending_type = None
        state.pending_breakout_level = None
        state.pending_sl = None
        state.breakout_done = False
        state.pending_entry_next_bar = False

        events.append({
            "type": "BUY_ENTRY" if state.trade_type == "BUY" else "SELL_ENTRY",
            "price": state.entry_price,
            "sl": state.sl_price,
            "target": state.target_price,
        })

    # check for a fresh breakout on this bar (only if we didn't just enter, and nothing queued)
    if not state.in_trade and not state.pending_entry_next_bar and state.pending_type and not state.breakout_done:
        if state.pending_type == "BUY" and h > state.pending_breakout_level:
            state.breakout_done = True
            state.pending_entry_next_bar = True
        if state.pending_type == "SELL" and l < state.pending_breakout_level:
            state.breakout_done = True
            state.pending_entry_next_bar = True

    # ===== STEP 5: while in a trade, check SL / Target / Trailing-SL =====
    close_reason = None

    if state.in_trade and not state.in_trailing_mode:
        if state.trade_type == "BUY":
            if l <= state.sl_price:
                close_reason = "SL"
            elif h >= state.target_price:
                close_reason = "TARGET_PARTIAL"
        else:
            if h >= state.sl_price:
                close_reason = "SL"
            elif l <= state.target_price:
                close_reason = "TARGET_PARTIAL"

        if exit_signal_now and close_reason is None:
            close_reason = "EXIT"

    if state.in_trade and state.in_trailing_mode:
        if state.trade_type == "BUY":
            if l <= state.sl_price:
                close_reason = "TRAIL_SL"
        else:
            if h >= state.sl_price:
                close_reason = "TRAIL_SL"

        if exit_signal_now and close_reason is None:
            close_reason = "EXIT"

    # ===== STEP 5b: TARGET_PARTIAL -> book 40%, switch to trailing =====
    if state.in_trade and close_reason == "TARGET_PARTIAL":
        state.in_trailing_mode = True
        state.outcomes.append(("TARGET", t))
        events.append({"type": "TARGET_PARTIAL", "price": c, "booked_pct": 40})

        # initial trail point = this bar's high/low
        state.sl_price = l if state.trade_type == "BUY" else h

    # ===== STEP 5c: trailing update each new bar (favorable direction only) =====
    if state.in_trade and state.in_trailing_mode and close_reason != "TARGET_PARTIAL" and close_reason is None:
        new_trail = l if state.trade_type == "BUY" else h
        moved_favorably = (new_trail > state.sl_price) if state.trade_type == "BUY" else (new_trail < state.sl_price)
        if moved_favorably:
            state.sl_price = new_trail

    # ===== STEP 6: full close on SL / TRAIL_SL / EXIT =====
    if state.in_trade and close_reason in ("SL", "TRAIL_SL", "EXIT"):
        events.append({
            "type": {"SL": "SL_HIT", "TRAIL_SL": "TRAIL_SL_HIT", "EXIT": "EXIT"}[close_reason],
            "price": c,
            "trade_type": state.trade_type,
            "entry": state.entry_price,
        })

        if close_reason == "SL":
            state.outcomes.append(("SL", t))
        if close_reason == "TRAIL_SL":
            state.outcomes.append(("TARGET", t))

        state.in_trade = False
        state.in_trailing_mode = False
        state.trade_type = None
        state.entry_price = None
        state.sl_price = None
        state.target_price = None

    state.prev_direction = direction
    return events


def win_rate_stats(state: SymbolState, days_back: int = 0, now_ms: Optional[int] = None) -> Dict[str, Any]:
    """All-time (days_back=0) or trailing-N-day win rate from state.outcomes."""
    if now_ms is None:
        import time
        now_ms = int(time.time() * 1000)
    cutoff = 0 if days_back == 0 else now_ms - days_back * 86400000
    sl = sum(1 for r, ts in state.outcomes if ts >= cutoff and r == "SL")
    tgt = sum(1 for r, ts in state.outcomes if ts >= cutoff and r == "TARGET")
    total = sl + tgt
    win_rate = (tgt / total * 100) if total > 0 else None
    return {"sl": sl, "target": tgt, "total": total, "win_rate": win_rate}
