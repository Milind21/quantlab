import numpy as np
import pandas as pd
from quantlab.backtest.vector import run_backtest
from quantlab.strategies.base import SignalFrame
from quantlab.report.metrics import compute_metrics

CFG = {
    "costs": {"commission_per_share": 0.0, "slippage_bps": 0.0},
    "risk": {"position_pct_cap": 1.0, "sector_pct_cap": 1.0, "max_positions": 1,
             "risk_per_trade": 1.0, "atr_stop_mult": 1000.0, "kill_switch_dd": 1.0},
    "regime": {"sma_window": 200, "band": 0.02, "exit_all": False},
}


def _rising_asset(n=600):
    idx = pd.date_range("2015-01-01", periods=n, freq="B")
    px = pd.Series(100 * (1.0003 ** np.arange(n)), index=idx)  # smooth riser -> regime ON, no stop hit
    df = pd.DataFrame({"open": px, "high": px, "low": px, "close": px}, index=idx).rename_axis("date")
    return {"SPY": df}, px


def _allin_signals(panel):
    close = pd.DataFrame({t: df["close"] for t, df in panel.items()})
    entry = pd.DataFrame(True, index=close.index, columns=close.columns)
    exit_ = pd.DataFrame(False, index=close.index, columns=close.columns)
    rank = pd.DataFrame(1.0, index=close.index, columns=close.columns)
    return SignalFrame(entry=entry, exit=exit_, rank=rank)


def test_buy_and_hold_engine_matches_asset_within_0p1pct_yr():
    """Engine-validation canary: fully-invested, zero-cost, stop disabled -> engine equity
    total-return tracks the asset's own total return (from entry) within ~0.1%/yr."""
    panel, px = _rising_asset()
    res = run_backtest(panel, _allin_signals(panel), CFG, spy_close=px, start_cash=100_000.0)
    # entry happens once regime turns ON (after SMA200 warm-up); measure from first nonzero exposure
    eq = res.equity.dropna()
    buys = res.trades[res.trades.side == "buy"]
    assert len(buys) == 1                      # bought once, held (no spurious churn)
    entry_date = buys.iloc[0]["date"]
    asset_ret = px.loc[entry_date:].iloc[-1] / px.loc[entry_date] - 1
    eng_ret = eq.iloc[-1] / eq.loc[entry_date] - 1
    yrs = len(px.loc[entry_date:]) / 252
    diff_per_yr = abs((1 + eng_ret) ** (1 / yrs) - (1 + asset_ret) ** (1 / yrs))
    assert diff_per_yr < 0.001, f"engine vs asset {diff_per_yr:.5f}/yr"


def test_determinism():
    panel, px = _rising_asset()
    sf = _allin_signals(panel)
    a = run_backtest(panel, sf, CFG, spy_close=px)
    b = run_backtest(panel, sf, CFG, spy_close=px)
    assert a.equity.equals(b.equity)
    assert compute_metrics(a.equity) == compute_metrics(b.equity)


def test_benchmark_is_spy_total_return():
    panel, px = _rising_asset()
    res = run_backtest(panel, _allin_signals(panel), CFG, spy_close=px)
    bench_ret = res.benchmark.iloc[-1] / res.benchmark.iloc[0] - 1
    spy_ret = px.iloc[-1] / px.iloc[0] - 1
    assert abs(bench_ret - spy_ret) < 1e-9
