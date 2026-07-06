"""Strategy protocol + SignalFrame. Strategies are PURE: (panel, params) -> SignalFrame.

The strategy emits only indicator-based, point-in-time-safe signals (entry candidate, exit,
rank). Path-dependent mechanics — held-state, regime gating, slot-filling by rank, ATR trailing
stop, time stop, kill-switch — are the engine/portfolio's job (portfolio.py), so the SAME
signal code drives the minimal backtest now and backtrader later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass
class SignalFrame:
    """Wide (date x ticker) signals. All aligned to the same index/columns."""
    entry: pd.DataFrame   # bool: is an entry candidate this bar
    exit: pd.DataFrame    # bool: indicator-based exit this bar
    rank: pd.DataFrame    # float: higher = preferred when filling slots (NaN where not a candidate)

    def tickers(self) -> list[str]:
        return list(self.entry.columns)


class Strategy(Protocol):
    name: str
    def signals(self, panel: dict[str, pd.DataFrame], params: dict) -> SignalFrame: ...


def _close_panel(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """dict[ticker->OHLCV] -> wide close DataFrame (date x ticker)."""
    return pd.DataFrame({t: df["close"] for t, df in panel.items()}).sort_index()
