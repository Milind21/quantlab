"""metrics — performance stats from an equity curve + trades. Pure."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _cagr(eq: pd.Series) -> float:
    yrs = len(eq) / TRADING_DAYS
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 and eq.iloc[0] > 0 else 0.0


def compute_metrics(eq: pd.Series, trades: pd.DataFrame | None = None) -> dict:
    r = eq.pct_change().dropna()
    vol = r.std() * np.sqrt(TRADING_DAYS)
    sharpe = (r.mean() * TRADING_DAYS) / vol if vol > 0 else 0.0
    downside = r[r < 0].std() * np.sqrt(TRADING_DAYS)
    sortino = (r.mean() * TRADING_DAYS) / downside if downside > 0 else 0.0
    dd = (eq / eq.cummax() - 1.0)
    max_dd = dd.min()
    cagr = _cagr(eq)
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    m = {"CAGR": cagr, "vol": vol, "Sharpe": sharpe, "Sortino": sortino,
         "max_drawdown": max_dd, "Calmar": calmar,
         "total_return": eq.iloc[-1] / eq.iloc[0] - 1.0, "n_trades": 0 if trades is None else len(trades)}
    return m
