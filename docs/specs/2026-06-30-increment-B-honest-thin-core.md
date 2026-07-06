# Increment B — Honest thin core

Master-plan phases 1, 2, 3(min), 4(min). Builds the real, honest trading core the
intelligence layer (Increment C) proposes against, and produces the first honest SPY
comparison. Decisions in the master plan §1 are locked.

## Goal
Pure, tested core — data → indicators → both strategy signal functions → portfolio/risk
logic → a **minimal vectorized backtest** → a minimal comparison report vs SPY. Enough that
(a) the param knobs in `configs/base.yaml` measurably change results (so Increment C has
something real to propose against), and (b) we get a first honest "do these beat SPY?" read.

## Scoping decision (explicit; does NOT relitigate the locked backtrader choice)
- **Now (B):** a minimal vectorized daily backtest driver. All trading LOGIC — position
  sizing, caps, ATR trailing stop with gap rule, regime filter, kill-switch — lives in PURE
  functions in `portfolio.py` / `regime.py`. The driver is thin wiring.
- **Later (post-C "rigor" increment):** the full **backtrader** event-driven engine (master-plan
  Phase 3) + look-ahead canary + determinism + validation/sweep harness (Phase 5). It will call
  the SAME pure portfolio/strategy functions — only the event loop differs, so nothing is rebuilt.
- Rationale: the capstone grade is on agent craft (C), not backtest-engine fidelity; the pure
  logic is the reusable asset and is written once. Strategy performance is tertiary (master-plan §0).

## Components (built/committed in this order)

### B1 — Data layer  (`src/quantlab/data/`)
- `provider.py` — `DataProvider` Protocol: `get_ohlcv(tickers, start, end) -> dict[str,DataFrame]`,
  `get_universe(as_of) -> list[str]`.
- `yf_provider.py` — yfinance impl, **parquet cache** under `data/` (gitignored), adjusted OHLCV.
  S&P 500 constituents via vendored CSV (with `as_of` recorded) or Wikipedia scrape; + SPY.
- `qa.py` — QA report: missing NYSE trading days, zero/negative prices, tickers with <300 bars
  (excluded with logged reasons), adjusted-split sanity (e.g. AAPL 2020-08-31 4:1 no artificial gap).
- Tests use a SMALL cached universe (SPY + ~20 names) for speed; full-universe pull is a
  cache-warming step run separately (may run in background), not required for tests.

### B2 — Indicators  (`src/quantlab/indicators.py`, pure)
- `sma, ema, rsi, atr, macd, bollinger, momentum, drawdown`. No I/O, no clock.
- Tested against hand-computed reference values incl. NaN warm-up and short-history edges.

### B3 — Strategies + portfolio/risk logic (pure)
- `strategies/base.py` — `Strategy` Protocol: `signals(panel, params) -> SignalFrame` (typed:
  entry/exit/stop columns per ticker). `strategies/trend_following.py`, `mean_reversion.py` per
  master-plan §4.3/§4.4.
- `portfolio.py` — pure sizing (`shares = risk_per_trade*equity/(entry-stop)`, capped by
  position_pct_cap), sector cap, ATR trailing stop **with gap rule** (open below stop ⇒ fill at
  open), kill-switch. `regime.py` — SPY SMA200 regime with hysteresis band.
- Property test: signals at date T unchanged when all data after T is deleted (no-lookahead).

### B4 — Minimal backtest + report
- `backtest/vector.py` — minimal vectorized driver: signal on close T → fill at open T+1 →
  apply costs (5 bps/side) → portfolio/risk logic → daily equity. Consumes the pure functions.
- `report/metrics.py` — CAGR, vol, Sharpe, Sortino, maxDD, Calmar, exposure, turnover, win rate,
  profit factor, #trades. `report/report.py` — minimal: a metrics table (both strategies + SPY
  benchmark) + equity-curve plot, written to `runs/<run_id>/`. (Full HTML/heatmaps deferred to Phase 4 proper.)
- CLI: `quantlab backtest --config <strategy.yaml>` runs end-to-end and writes the run dir;
  `quantlab report --runs <a> <b>` emits the comparison.

## Acceptance criteria
- [ ] Data: small-universe daily OHLCV cached; 2nd call is a cache hit (no network). QA report
      flags missing days / bad prices / short history with reasons. AAPL 4:1 split shows no artificial gap.
- [ ] Indicators unit-tested vs hand-computed references (incl. warm-up NaNs).
- [ ] `TrendFollowing.signals()` / `MeanReversion.signals()` produce expected entries/exits on a
      synthetic fixture panel with known outputs; **no-lookahead property test passes**.
- [ ] Gap-through-stop unit test: a series gapping 15% below the stop fills at the OPEN, not the stop.
- [ ] Determinism: same config + same cached data ⇒ identical metrics.json (two runs).
- [ ] Buy-and-hold-SPY through the engine at zero cost matches SPY adjusted total return within
      ~0.1%/yr (engine-validation sanity).
- [ ] `quantlab backtest --config configs/trend_following.yaml` and `mean_reversion.yaml` run
      end-to-end on the small universe; `quantlab report` emits a metrics table vs SPY + equity plot.
- [ ] Report header prints standing caveats (survivorship, fundamentals-not-backtested, taxes).
- [ ] Core stays import-pure (extend `test_import_purity.py` to indicators/strategies/portfolio/regime).

## Out of scope for B (later increments)
Full backtrader engine, look-ahead canary on real data, parameter sweeps + holdout harness
(Phase 5), live fundamental screen (Phase 6), Alpaca paper (Phase 7), the intelligence layer (C),
full HTML report + monthly-returns heatmaps. Full 500-ticker run is optional cache-warming.
