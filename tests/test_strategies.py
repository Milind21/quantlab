import numpy as np
import pandas as pd
from quantlab.strategies.trend_following import TrendFollowing
from quantlab.strategies.mean_reversion import MeanReversion


def _panel(close, n=None):
    idx = pd.date_range("2020-01-01", periods=len(close), freq="B")
    s = pd.Series(close, index=idx, dtype=float)
    df = pd.DataFrame({"open": s, "high": s * 1.01, "low": s * 0.99, "close": s})
    return {"AAA": df}


def test_tf_enters_in_uptrend():
    # long rising series -> eventually close>SMA50>SMA200 -> entry True near the end
    close = np.linspace(50, 150, 320)
    sf = TrendFollowing().signals(_panel(close), {})
    assert sf.entry["AAA"].iloc[-1]              # uptrend -> entry candidate
    # no entries before SMA200 is even defined (first non-NaN at index 199)
    assert not sf.entry["AAA"].iloc[:199].any()


def test_tf_exit_two_consecutive_below():
    # rise then sharp drop -> 2 consecutive closes below SMA50 triggers exit
    close = np.concatenate([np.linspace(50, 150, 300), np.linspace(150, 90, 40)])
    sf = TrendFollowing().signals(_panel(close), {})
    assert sf.exit["AAA"].iloc[-1]


def test_mr_entry_equals_oversold_in_uptrend():
    # Behavioral test: a long uptrend with a sharp recent dip. Assert the strategy's entry
    # flag exactly equals (close>SMA200) & (RSI(14)<30), verified via the indicators directly
    # — so the test holds regardless of whether the fixture happens to be oversold.
    from quantlab import indicators as ind
    base = np.linspace(100, 300, 300)                 # steep uptrend -> SMA200 well below close
    dip = base.copy()
    dip[-12:] = base[-12] * (0.985 ** np.arange(1, 13))  # 12-day ~1.5%/day decline -> low RSI
    panel = _panel(dip)
    sf = MeanReversion().signals(panel, {})
    c = panel["AAA"]["close"]
    cond = (c > ind.sma(c, 200)) & (ind.rsi(c, 14) < 30)
    cond = cond.fillna(False)
    assert np.array_equal(sf.entry["AAA"].to_numpy(), cond.to_numpy())
    assert sf.entry["AAA"].iloc[-1]                   # and this fixture IS oversold-in-uptrend


def test_no_lookahead_property():
    # signals at date T must not change when future data is deleted
    rng = np.random.RandomState(1)
    close = 100 + np.cumsum(rng.normal(0, 1, 400))
    full = _panel(close)
    for Strat in (TrendFollowing, MeanReversion):
        sf_full = Strat().signals(full, {})
        T = 350
        truncated = {t: df.iloc[: T + 1] for t, df in full.items()}
        sf_trunc = Strat().signals(truncated, {})
        # entry/exit at every date <= T identical
        a = sf_full.entry["AAA"].iloc[: T + 1].to_numpy()
        b = sf_trunc.entry["AAA"].to_numpy()
        assert np.array_equal(a, b), f"{Strat.__name__} entry leaks future"
        a2 = sf_full.exit["AAA"].iloc[: T + 1].to_numpy()
        b2 = sf_trunc.exit["AAA"].to_numpy()
        assert np.array_equal(a2, b2), f"{Strat.__name__} exit leaks future"
