"""portfolio — pure position-sizing, stop, and risk logic (master-plan §4.1). No I/O.

These functions are shared by the minimal vector engine now and the backtrader engine later,
so the trading LOGIC is written once. Path-dependent state (highest close since entry, prior
stop, equity peak) is passed in by the caller — the functions themselves are pure.
"""
from __future__ import annotations

import math


def position_size(equity: float, entry_price: float, stop_price: float,
                  risk_per_trade: float, position_pct_cap: float) -> int:
    """Risk-based sizing capped by notional. shares = risk$ / per-share-risk, then notional cap.

    Returns whole shares (>=0). Guards against non-positive per-share risk.
    """
    per_share_risk = entry_price - stop_price
    if per_share_risk <= 0 or entry_price <= 0:
        return 0
    risk_shares = (risk_per_trade * equity) / per_share_risk
    cap_shares = (position_pct_cap * equity) / entry_price
    return int(max(0, math.floor(min(risk_shares, cap_shares))))


def initial_stop(entry_price: float, atr_at_entry: float, mult: float) -> float:
    """Initial stop = entry - mult*ATR."""
    return entry_price - mult * atr_at_entry


def trailing_stop(prev_stop: float, highest_close_since_entry: float, atr_now: float,
                  mult: float) -> float:
    """Ratcheting trailing stop: never decreases. = max(prev, highest_close - mult*ATR)."""
    candidate = highest_close_since_entry - mult * atr_now
    return max(prev_stop, candidate)


def stop_fill_price(open_price: float, stop_price: float, low_price: float) -> float | None:
    """Gap rule (master-plan §4.1). Returns fill price if the stop is hit this bar, else None.

    - If the bar OPENS at/below the stop, fill at the OPEN (gapped through — never at the stop).
    - Else if the intrabar LOW pierces the stop, fill at the stop price.
    """
    if open_price <= stop_price:
        return open_price
    if low_price <= stop_price:
        return stop_price
    return None


def kill_switch_triggered(equity: float, peak_equity: float, threshold: float) -> bool:
    """True when drawdown from peak exceeds `threshold` (e.g. 0.20)."""
    if peak_equity <= 0:
        return False
    return (equity / peak_equity - 1.0) <= -abs(threshold)
