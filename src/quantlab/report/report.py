"""report — minimal comparison report: metrics table + equity-curve plot vs SPY.

Standing caveats printed in the header (master-plan §4). Full HTML/heatmaps deferred to Phase 4.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .metrics import compute_metrics

CAVEATS = (
    "CAVEATS: survivorship bias (current constituents); fundamentals NOT backtested; "
    "taxes NOT modeled; yfinance data best-effort."
)


def comparison(results: dict[str, "object"], out_dir: Path | str) -> Path:
    """results: {name -> BacktestResult}. Writes metrics.csv + equity.png + report.txt."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    rows = {}
    fig, ax = plt.subplots(figsize=(10, 5))
    bench_plotted = False
    for name, res in results.items():
        rows[name] = compute_metrics(res.equity, res.trades)
        ax.plot(res.equity.index, res.equity.values, label=name)
        if res.benchmark is not None and not bench_plotted:
            ax.plot(res.benchmark.index, res.benchmark.values, "k--", label="SPY (buy&hold)")
            rows["SPY_buyhold"] = compute_metrics(res.benchmark)
            bench_plotted = True
    ax.set_title("Equity curves vs SPY"); ax.legend(); ax.set_ylabel("equity ($)")
    fig.tight_layout(); fig.savefig(out / "equity.png", dpi=110); plt.close(fig)

    table = pd.DataFrame(rows).T
    table.to_csv(out / "metrics.csv")
    lines = [CAVEATS, "", table.round(4).to_string()]
    (out / "report.txt").write_text("\n".join(lines))
    return out
