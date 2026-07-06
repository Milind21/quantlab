import numpy as np
import pandas as pd
from quantlab import indicators as ind


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = ind.sma(s, 3)
    assert out.iloc[:2].isna().all()              # warm-up NaN
    assert out.iloc[2] == 2.0 and out.iloc[4] == 4.0


def test_momentum():
    s = pd.Series([100, 110, 121], dtype=float)
    out = ind.momentum(s, 1)
    assert out.iloc[0] != out.iloc[0] or np.isnan(out.iloc[0])  # NaN first
    assert abs(out.iloc[1] - 0.10) < 1e-9
    assert abs(out.iloc[2] - 0.10) < 1e-9


def test_rsi_all_gains_is_100():
    s = pd.Series(np.arange(1, 30, dtype=float))   # strictly increasing
    r = ind.rsi(s, 14)
    assert r.iloc[:14].isna().all()                # warm-up
    assert abs(r.iloc[-1] - 100.0) < 1e-6


def test_rsi_reference_value():
    # Hand-checkable: constant-up then flat doesn't crash; RSI in [0,100]
    s = pd.Series([44,44.3,44.1,44.6,44.3,44.8,45.1,45.4,45.4,45.2,46.6,46.3,46.3,46,46.1,46.6], dtype=float)
    r = ind.rsi(s, 14)
    assert ((r.dropna() >= 0) & (r.dropna() <= 100)).all()
    assert r.notna().iloc[-1]


def test_atr_positive_and_warmup():
    n = 30
    high = pd.Series(np.linspace(10, 20, n))
    low = high - 1.0
    close = high - 0.5
    a = ind.atr(high, low, close, 14)
    assert a.iloc[:13].isna().all()
    assert (a.dropna() > 0).all()


def test_bollinger_band_order():
    s = pd.Series(np.random.RandomState(0).normal(100, 5, 100))
    mid, up, lo = ind.bollinger(s, 20, 2.0)
    d = pd.concat([lo, mid, up], axis=1).dropna()
    assert (d.iloc[:, 0] <= d.iloc[:, 1]).all() and (d.iloc[:, 1] <= d.iloc[:, 2]).all()


def test_macd_hist_is_line_minus_signal():
    s = pd.Series(np.random.RandomState(1).normal(100, 3, 200))
    line, sig, hist = ind.macd(s)
    assert np.allclose((line - sig).dropna(), hist.dropna())


def test_drawdown_non_positive():
    eq = pd.Series([1.0, 1.1, 1.05, 1.2, 0.9])
    dd = ind.drawdown(eq)
    assert (dd <= 1e-12).all()
    assert abs(dd.iloc[-1] - (0.9 / 1.2 - 1.0)) < 1e-12
