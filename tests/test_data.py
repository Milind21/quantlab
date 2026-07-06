import numpy as np
import pandas as pd
import pytest
from quantlab.data.yf_provider import YFinanceProvider
from quantlab.data import qa


def _fake_ohlcv(n=400, start="2018-01-01"):
    idx = pd.date_range(start, periods=n, freq="B")
    px = pd.Series(100 + np.cumsum(np.random.RandomState(0).normal(0, 1, n)), index=idx)
    return pd.DataFrame({"open": px, "high": px * 1.01, "low": px * 0.99,
                         "close": px, "volume": 1_000_000}, index=idx).rename_axis("date")


def test_cache_hit_no_network(tmp_path, monkeypatch):
    prov = YFinanceProvider(cache_dir=tmp_path)
    # pre-write a cache file; _download must NOT be called
    _fake_ohlcv().to_parquet(tmp_path / "AAA.parquet")
    def boom(*a, **k):
        raise AssertionError("network called on a cache hit")
    monkeypatch.setattr(prov, "_download", boom)
    out = prov.get_ohlcv(["AAA"], start="2018-06-01")
    assert len(out["AAA"]) > 0
    assert out["AAA"].index.min() >= pd.Timestamp("2018-06-01")  # sliced to requested start


def test_universe_loads():
    prov = YFinanceProvider()
    uni = prov.get_universe()
    assert "AAPL" in uni and len(uni) >= 20


def test_qa_flags_bad_and_short():
    good = _fake_ohlcv(400)
    short = _fake_ohlcv(50)
    bad = _fake_ohlcv(400).copy(); bad.loc[bad.index[10], "close"] = -5.0
    rep = qa.qa_report({"GOOD": good, "SHORT": short, "BAD": bad})
    assert "SHORT" in rep["excluded"] and "BAD" in rep["excluded"]
    assert "GOOD" not in rep["excluded"]
    clean, excl = qa.filter_panel({"GOOD": good, "SHORT": short})
    assert list(clean) == ["GOOD"]


def test_cached_aapl_split_no_artificial_gap():
    """AAPL 2020-08-31 4:1 split: auto_adjust=True -> no ~75% one-day artificial gap.
    Uses the real warmed cache if present; skips cleanly if not."""
    prov = YFinanceProvider()
    out = prov.get_ohlcv(["AAPL"], start="2020-08-01", end="2020-09-15")
    df = out["AAPL"]
    if len(df) < 10:
        pytest.skip("AAPL cache not warmed")
    ret = df["close"].pct_change().abs()
    assert ret.max() < 0.2  # adjusted -> no split-induced ~75% jump
