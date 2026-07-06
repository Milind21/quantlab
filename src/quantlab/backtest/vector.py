"""vector — minimal long-only daily backtest. Signal on close T, fill at open T+1.

Reuses the PURE portfolio/regime logic (portfolio.py, regime.py) so the trading rules are
written once and the future backtrader engine reuses them. Path-dependent state lives here;
the rules it calls are pure. Sector caps deferred (no sector metadata cached yet) — noted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import indicators as ind
from .. import portfolio as pf
from ..regime import regime_series
from ..strategies.base import SignalFrame


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    config: dict
    benchmark: pd.Series = field(default=None)


def _wide(panel, field):
    return pd.DataFrame({t: df[field] for t, df in panel.items()}).sort_index()


def run_backtest(panel: dict[str, pd.DataFrame], sf: SignalFrame, cfg: dict,
                 spy_close: pd.Series, time_stop: int | None = None,
                 start_cash: float = 100_000.0) -> BacktestResult:
    risk = cfg["risk"]; reg = cfg["regime"]; costs = cfg["costs"]
    slip = costs["slippage_bps"] / 1e4
    mult = risk["atr_stop_mult"]
    max_pos = int(risk["max_positions"])
    dates = sf.entry.index
    opens, highs, lows, closes = (_wide(panel, k) for k in ("open", "high", "low", "close"))
    atr = pd.DataFrame({t: ind.atr(panel[t]["high"], panel[t]["low"], panel[t]["close"], 14)
                        for t in panel}).reindex(dates)
    regime = regime_series(spy_close.reindex(dates).ffill(), reg["sma_window"], reg["band"]).reindex(dates).fillna(False)

    cash = start_cash
    pos: dict[str, dict] = {}              # ticker -> {shares, entry, stop, hi, entry_i}
    peak = start_cash
    halted = False
    entry_q: list[str] = []
    exit_q: list[str] = []
    eq = pd.Series(index=dates, dtype=float)
    trades = []

    def equity_now(i):
        mtm = sum(p["shares"] * closes[t].iloc[i] for t, p in pos.items() if not np.isnan(closes[t].iloc[i]))
        return cash + mtm

    for i, d in enumerate(dates):
        if i == 0:
            eq.iloc[i] = cash
            continue
        # --- open[i]: 1) stop hits, 2) queued exits, 3) queued entries ---
        for t in list(pos):
            o, lo = opens[t].iloc[i], lows[t].iloc[i]
            if np.isnan(o):
                continue
            fill = pf.stop_fill_price(o, pos[t]["stop"], lo)
            if fill is not None:
                px = fill * (1 - slip)
                cash += pos[t]["shares"] * px
                trades.append({"date": d, "ticker": t, "side": "sell_stop", "shares": pos[t]["shares"], "price": px})
                del pos[t]
        for t in exit_q:
            if t in pos and not np.isnan(opens[t].iloc[i]):
                px = opens[t].iloc[i] * (1 - slip)
                cash += pos[t]["shares"] * px
                trades.append({"date": d, "ticker": t, "side": "sell", "shares": pos[t]["shares"], "price": px})
                del pos[t]
        for t in entry_q:
            if t in pos or len(pos) >= max_pos:
                continue
            o = opens[t].iloc[i]; a = atr[t].iloc[i - 1]
            if np.isnan(o) or np.isnan(a) or a <= 0:
                continue
            stop = pf.initial_stop(o, a, mult)
            shares = pf.position_size(equity_now(i), o, stop, risk["risk_per_trade"], risk["position_pct_cap"])
            cost = shares * o * (1 + slip)
            if shares > 0 and cost <= cash:
                cash -= cost
                pos[t] = {"shares": shares, "entry": o, "stop": stop, "hi": o, "entry_i": i}
                trades.append({"date": d, "ticker": t, "side": "buy", "shares": shares, "price": o * (1 + slip)})

        # --- close[i]: update stops, MTM, kill-switch, build next-day queues ---
        for t, p in pos.items():
            c, a = closes[t].iloc[i], atr[t].iloc[i]
            if not np.isnan(c):
                p["hi"] = max(p["hi"], c)
            if not np.isnan(a):
                p["stop"] = pf.trailing_stop(p["stop"], p["hi"], a, mult)
        equity = equity_now(i)
        eq.iloc[i] = equity
        peak = max(peak, equity)

        exit_q, entry_q = [], []
        if pf.kill_switch_triggered(equity, peak, risk["kill_switch_dd"]):
            halted = True
            exit_q = list(pos)                      # liquidate next open
            continue
        if halted:
            continue
        # indicator + time-stop exits
        for t, p in pos.items():
            ind_exit = bool(sf.exit[t].iloc[i]) if t in sf.exit else False
            time_exit = time_stop is not None and (i - p["entry_i"]) >= time_stop
            if ind_exit or time_exit:
                exit_q.append(t)
        # entries: regime gate + slot fill by rank
        if not regime.iloc[i]:
            if reg.get("exit_all", False):
                exit_q = list(pos)
        else:
            free = max_pos - (len(pos) - len(exit_q))
            if free > 0:
                cand = sf.rank.iloc[i].dropna()
                cand = cand[[t for t in cand.index if t not in pos]]
                entry_q = list(cand.sort_values(ascending=False).head(free).index)

    eq = eq.ffill()
    bench = (spy_close.reindex(dates).ffill() / spy_close.reindex(dates).ffill().iloc[0]) * start_cash
    return BacktestResult(equity=eq, trades=pd.DataFrame(trades), config=cfg, benchmark=bench)
