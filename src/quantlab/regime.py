"""regime — SPY SMA200 regime filter with hysteresis (master-plan §4.2). Pure.

Risk-ON when SPY close > SMA200. Switches OFF only when close < (1-band)*SMA200; switches back
ON only when close > SMA200. The band kills whipsaw. Stateful pass (path-dependent), but a pure
function of the input series.
"""
from __future__ import annotations

import pandas as pd

from . import indicators as ind


def regime_series(spy_close: pd.Series, sma_window: int = 200, band: float = 0.02) -> pd.Series:
    sma = ind.sma(spy_close, sma_window)
    on = pd.Series(False, index=spy_close.index)
    state = False
    for i in range(len(spy_close)):
        c, m = spy_close.iloc[i], sma.iloc[i]
        if pd.isna(m):
            on.iloc[i] = False
            continue
        if state:
            if c < (1 - band) * m:
                state = False
        else:
            if c > m:
                state = True
        on.iloc[i] = state
    return on
