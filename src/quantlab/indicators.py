"""indicators — pure technical-analysis functions. No I/O, no clock, no global state.

All take a pandas Series of (adjusted) prices indexed by date and return a Series aligned to
the input; warm-up periods are NaN. Classic, interpretable indicators only (master-plan §1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window, min_periods=window).mean()


def ema(s: pd.Series, span: int) -> pd.Series:
    # Wilder/standard EMA via pandas; first (span-1) are NaN to mark warm-up explicitly.
    out = s.ewm(span=span, adjust=False).mean()
    out.iloc[: span - 1] = np.nan
    return out


def rsi(s: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's RSI. NaN for the first `window` rows."""
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    # Wilder smoothing = EMA with alpha = 1/window
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - 100.0 / (1.0 + rs)
    out[avg_loss == 0] = 100.0  # all-gains window -> RSI 100
    return out


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range (Wilder). True range uses prior close."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    macd_line = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def bollinger(s: pd.Series, window: int = 20, n_std: float = 2.0):
    """Returns (mid, upper, lower)."""
    mid = sma(s, window)
    sd = s.rolling(window, min_periods=window).std(ddof=0)
    return mid, mid + n_std * sd, mid - n_std * sd


def momentum(s: pd.Series, window: int) -> pd.Series:
    """Total return over `window` bars (close_t / close_{t-window} - 1)."""
    return s / s.shift(window) - 1.0


def drawdown(equity: pd.Series) -> pd.Series:
    """Drawdown from running peak (<= 0)."""
    return equity / equity.cummax() - 1.0
