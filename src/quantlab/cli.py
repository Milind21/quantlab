"""cli — QuantLab commands. Increment B wires real `backtest` + `report`."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from .backtest.vector import run_backtest
from .config import load_config
from .data.qa import filter_panel
from .data.yf_provider import YFinanceProvider
from .manifest import write_manifest
from .report.metrics import compute_metrics
from .report.report import comparison
from .strategies.mean_reversion import MeanReversion
from .strategies.trend_following import TrendFollowing

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"
STRATS = {"trend_following": TrendFollowing, "mean_reversion": MeanReversion}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _backtest(args):
    raw = yaml.safe_load(Path(args.config).read_text())
    cfg = load_config(args.config)
    if args.dry_run:
        rd = write_manifest(RUNS, cfg, _ts(), extra={"mode": "dry-run"})
        print(f"[dry-run] manifest: {rd/'manifest.json'}")
        return
    name = raw.get("strategy", "trend_following")
    prov = YFinanceProvider()
    uni = prov.get_universe()
    panel = prov.get_ohlcv(uni, start=cfg.backtest.start)
    panel, excluded = filter_panel(panel)
    spy = prov.get_ohlcv(["SPY"], start=cfg.backtest.start)["SPY"]["close"]
    strat = STRATS[name]()
    sf = strat.signals(panel, raw)
    time_stop = raw.get("mean_reversion", {}).get("time_stop") if name == "mean_reversion" else None
    res = run_backtest(panel, sf, cfg.model_dump(exclude={"tunable"}), spy, time_stop=time_stop)
    rd = write_manifest(RUNS, cfg, _ts(), extra={"strategy": name, "excluded": excluded})
    res.equity.to_frame("equity").to_parquet(rd / "equity.parquet")
    res.benchmark.to_frame("benchmark").to_parquet(rd / "benchmark.parquet")
    res.trades.to_csv(rd / "trades.csv", index=False)
    m = compute_metrics(res.equity, res.trades)
    (rd / "metrics.json").write_text(json.dumps(m, indent=2))
    print(f"[{name}] run {rd.name}  CAGR={m['CAGR']:.4f} Sharpe={m['Sharpe']:.2f} "
          f"maxDD={m['max_drawdown']:.4f} trades={m['n_trades']}")
    bm = compute_metrics(res.benchmark)
    print(f"  SPY buy&hold: CAGR={bm['CAGR']:.4f} Sharpe={bm['Sharpe']:.2f}")
    print(f"  run dir: {rd}")


class _R:  # lightweight holder for report reload
    def __init__(self, equity, benchmark, trades):
        self.equity, self.benchmark, self.trades = equity, benchmark, trades


def _report(args):
    results = {}
    for rid in args.runs:
        rd = RUNS / rid
        eq = pd.read_parquet(rd / "equity.parquet")["equity"]
        bm = pd.read_parquet(rd / "benchmark.parquet")["benchmark"]
        man = json.loads((rd / "manifest.json").read_text())
        results[man.get("strategy", rid)] = _R(eq, bm, None)
    out = comparison(results, RUNS / "comparison")
    print(f"comparison report: {out}")
    print((out / "report.txt").read_text())


def _active_config() -> Path:
    """The live, mutable config the intelligence layer targets (copy of base.yaml on first use)."""
    active = ROOT / "configs" / "active.yaml"
    if not active.exists():
        active.write_text((ROOT / "configs" / "base.yaml").read_text())
    return active


def _make_llm(live: bool):
    from .intelligence.llm import GeminiLLMClient, MockLLMClient
    if live:
        try:
            return GeminiLLMClient()
        except Exception as e:
            print(f"[warn] Gemini unavailable ({e}); falling back to MockLLMClient")
    return MockLLMClient()


def _intel(args):
    from datetime import date, timedelta
    from .config import load_config
    from .intelligence.agents import run_pipeline
    from .intelligence.memory import SentimentMemory
    from .intelligence.proposals import ProposalStore
    from .intelligence.sources.fixture import FixtureSource

    cfg = load_config(_active_config())
    run_date = args.date or date.today().isoformat()
    expires = (date.fromisoformat(run_date) + timedelta(days=7)).isoformat()
    # Fixture posts are always the base (deterministic demo); --live adds real sources best-effort
    # (each is resilient in the collector). --live independently controls the Gemini LLM.
    sources = [FixtureSource()]
    if args.live:
        import os as _os
        from .intelligence.sources.stocktwits import StockTwitsSource
        sources.append(StockTwitsSource())                    # no key needed
        if _os.environ.get("REDDIT_CLIENT_ID"):
            from .intelligence.sources.reddit import RedditSource
            sources.append(RedditSource())
    mem = SentimentMemory(RUNS / "intel.db")
    rep = run_pipeline(args.watchlist, sources, _make_llm(args.live), mem,
                       cfg.model_dump(exclude={"tunable"}), cfg.tunable, run_date,
                       since=0.0, expires_at=expires)
    out = RUNS / "intel" / run_date
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"QuantLab intelligence report — {run_date}", "=" * 48, rep.summary, ""]
    for tk, v in rep.views.items():
        lines.append(f"[{tk}] {v.label} score={v.score:+.2f} delta={v.delta} themes={v.themes} "
                     f"critic={'organic' if rep.critics[tk].organic else 'SUSPECT'} ({rep.critics[tk].note})")
    store = ProposalStore(RUNS / "proposals", _active_config())
    if rep.proposals:
        lines.append("\nPROPOSALS (pending human review — inert until approved):")
        for p in rep.proposals:
            pid = store.submit(p)
            lines.append(f"  [{pid}] {p.param}: {p.current} -> {p.proposed}  (conf {p.confidence:.2f}) {p.rationale}")
    (out / "report.txt").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nreport: {out/'report.txt'}")


def _proposals(args):
    from .intelligence.proposals import ProposalStore
    store = ProposalStore(RUNS / "proposals", _active_config())
    if args.approve:
        res = store.approve(args.approve)
        print(res)
        if res.get("applied"):
            print(f"  applied {res['param']}: {res['from']} -> {res['to']}")
            print(f"  to revert:  quantlab proposals --rollback {res['prev_version']}")
    elif args.reject:
        print(store.reject(args.reject))
    elif args.rollback:
        print(store.rollback(args.rollback))
    else:
        pend = store.list_pending()
        if not pend:
            print("no pending proposals")
        for pid, p in pend:
            print(f"[{pid}] {p.param}: {p.current} -> {p.proposed} (conf {p.confidence:.2f})")
            print(f"        {p.rationale}")


def _stub(name):
    def fn(args):
        print(f"`{name}` not implemented yet (later increment)")
    return fn


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quantlab")
    sub = p.add_subparsers(dest="cmd", required=True)
    bt = sub.add_parser("backtest"); bt.add_argument("--config", required=True)
    bt.add_argument("--dry-run", action="store_true"); bt.set_defaults(func=_backtest)
    rp = sub.add_parser("report"); rp.add_argument("--runs", nargs="+", required=True)
    rp.set_defaults(func=_report)
    it = sub.add_parser("intel", help="run the multi-agent intelligence pipeline")
    it.add_argument("--watchlist", nargs="+", required=True)
    it.add_argument("--live", action="store_true", help="use Gemini + live sources (needs keys)")
    it.add_argument("--date", help="run date YYYY-MM-DD (default today)")
    it.set_defaults(func=_intel)
    pr = sub.add_parser("proposals", help="review queue: list / approve / reject / rollback")
    pr.add_argument("--approve"); pr.add_argument("--reject"); pr.add_argument("--rollback")
    pr.set_defaults(func=_proposals)
    for name in ("sweep", "screen", "paper-run"):
        sp = sub.add_parser(name); sp.set_defaults(func=_stub(name))
    return p


def main(argv=None):
    # load .env (Gemini/Reddit keys) for live mode; no-op if missing
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
