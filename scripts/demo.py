"""demo.py — stage a realistic scenario so the review-queue flow is demoable on camera.

The built-in fixture has no prior history, so `quantlab intel` alone won't emit a proposal
(delta-vs-baseline is None). This seeds a bullish baseline for a demo ticker, then runs the
pipeline over organic *bearish* posts — producing exactly one bounded, tighten-only proposal
in the review queue. After running this, demo:

    python scripts/demo.py
    quantlab proposals                 # -> one pending proposal (inert)
    quantlab proposals --approve <id>  # -> config 0.05 -> 0.035, versioned + audited
    quantlab proposals --rollback <ver>
"""
from pathlib import Path

from quantlab.config import load_config
from quantlab.intelligence.agents import run_pipeline
from quantlab.intelligence.llm import MockLLMClient
from quantlab.intelligence.memory import SentimentMemory
from quantlab.intelligence.proposals import ProposalStore
from quantlab.intelligence.sources.fixture import FixtureSource

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
TICKER = "ACME"


def _active():
    a = ROOT / "configs" / "active.yaml"
    if not a.exists():
        a.write_text((ROOT / "configs" / "base.yaml").read_text())
    return a


def main():
    cfg = load_config(_active())
    mem = SentimentMemory(RUNS / "intel.db")
    # 1) establish a BULLISH baseline over prior runs
    for d in ("2026-07-01", "2026-07-02", "2026-07-03"):
        mem.record(d, TICKER, 0.8, 5)
    # 2) today: organic BEARISH posts (many distinct authors, no dup text, no manipulation cues)
    seed = [(TICKER, f"trader{i}", t, "bear") for i, t in enumerate([
        "ACME downgrade, weak guidance, bearish",
        "ACME misses estimates, macro headwinds, sell",
        "ACME plunge on litigation, downgrade",
        "ACME bearish breakdown, dump",
        "ACME weak demand, sell rating"])]
    rep = run_pipeline([TICKER], [FixtureSource(seed=seed)], MockLLMClient(), mem,
                       cfg.model_dump(exclude={"tunable"}), cfg.tunable,
                       run_date="2026-07-06", since=0.0, expires_at="2026-07-13")
    store = ProposalStore(RUNS / "proposals", _active())
    ids = [store.submit(p) for p in rep.proposals]
    print(f"\nScenario staged for {TICKER}: {rep.summary}")
    print(f"Submitted {len(ids)} proposal(s) to the review queue: {ids}")
    print("\nNow run:  quantlab proposals            (see it pending, inert)")
    print("          quantlab proposals --approve <id>")


if __name__ == "__main__":
    main()
