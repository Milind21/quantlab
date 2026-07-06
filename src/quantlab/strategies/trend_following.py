"""Trend-following (master-plan §4.3). Pure.

Entry candidate: close > SMA50 AND SMA50 > SMA200 (regime + not-held applied by engine).
Rank: 126-day momentum, descending (higher = preferred).
Indicator exit: close < SMA50 for 2 consecutive closes. (ATR trailing stop + kill-switch: engine.)
"""
from __future__ import annotations

import pandas as pd

from .. import indicators as ind
from .base import SignalFrame, _close_panel


class TrendFollowing:
    name = "trend_following"

    def signals(self, panel: dict[str, pd.DataFrame], params: dict) -> SignalFrame:
        p = params.get("trend_following", {})
        sma_fast = int(p.get("sma_fast", 50))
        sma_slow = int(p.get("sma_slow", 200))
        mom_window = int(p.get("momentum_window", 126))
        close = _close_panel(panel)
        f = close.apply(lambda s: ind.sma(s, sma_fast))
        sl = close.apply(lambda s: ind.sma(s, sma_slow))
        mom = close.apply(lambda s: ind.momentum(s, mom_window))

        uptrend = (close > f) & (f > sl)
        entry = uptrend.fillna(False)
        below = (close < f).fillna(False)
        exit_ = (below & below.shift(1).fillna(False))
        rank = mom.where(entry)
        return SignalFrame(entry=entry, exit=exit_, rank=rank)
