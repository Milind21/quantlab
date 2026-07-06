"""Mean-reversion (master-plan §4.4). Pure.

Qualifier: close > SMA200 (buy dips inside long uptrends; regime applied by engine).
Entry: RSI(rsi_window) < rsi_buy. Rank: lowest RSI first (rank = -RSI, higher = preferred).
Indicator exit: RSI > rsi_exit. (10-day time stop + ATR hard stop + kill-switch: engine.)
Sweep variant (Phase 5): rsi_window=2, rsi_buy=10 (Connors).
"""
from __future__ import annotations

import pandas as pd

from .. import indicators as ind
from .base import SignalFrame, _close_panel


class MeanReversion:
    name = "mean_reversion"

    def signals(self, panel: dict[str, pd.DataFrame], params: dict) -> SignalFrame:
        p = params.get("mean_reversion", {})
        sma_slow = int(p.get("sma_slow", 200))
        rsi_window = int(p.get("rsi_window", 14))
        rsi_buy = float(p.get("rsi_buy", 30))
        rsi_exit = float(p.get("rsi_exit", 55))
        close = _close_panel(panel)
        sl = close.apply(lambda s: ind.sma(s, sma_slow))
        r = close.apply(lambda s: ind.rsi(s, rsi_window))

        qualifier = (close > sl).fillna(False)
        entry = (qualifier & (r < rsi_buy)).fillna(False)
        exit_ = (r > rsi_exit).fillna(False)
        rank = (-r).where(entry)   # lowest RSI -> highest rank
        return SignalFrame(entry=entry, exit=exit_, rank=rank)
