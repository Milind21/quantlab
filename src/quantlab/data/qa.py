"""qa — data-quality checks on an OHLCV panel. Pure (operates on in-memory frames).

Flags zero/negative prices, too-short history, and large adjusted-price gaps; returns a report
plus a filtered panel (tickers failing hard checks excluded, with logged reasons).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_BARS = 300
MAX_DAILY_JUMP = 0.5  # |daily close-to-close| > 50% flagged as a possible bad/unadjusted bar


def qa_report(panel: dict[str, pd.DataFrame], min_bars: int = MIN_BARS) -> dict:
    rows, excluded = [], {}
    for t, df in panel.items():
        n = len(df)
        bad_price = bool((df[["open", "high", "low", "close"]] <= 0).any().any()) if n else True
        ret = df["close"].pct_change() if n else pd.Series(dtype=float)
        big_jumps = int((ret.abs() > MAX_DAILY_JUMP).sum())
        reasons = []
        if n < min_bars:
            reasons.append(f"short_history({n}<{min_bars})")
        if bad_price:
            reasons.append("zero_or_negative_price")
        if reasons:
            excluded[t] = reasons
        rows.append({"ticker": t, "bars": n, "bad_price": bad_price,
                     "big_jumps": big_jumps, "excluded": bool(reasons)})
    return {"summary": pd.DataFrame(rows), "excluded": excluded}


def filter_panel(panel: dict[str, pd.DataFrame], min_bars: int = MIN_BARS):
    """Return (clean_panel, excluded_dict)."""
    rep = qa_report(panel, min_bars)
    clean = {t: df for t, df in panel.items() if t not in rep["excluded"]}
    return clean, rep["excluded"]
