"""demo.py — stage a realistic scenario so the review-queue flow is demoable on camera.

The built-in fixture has no prior history, so `quantlab intel` alone won't emit a proposal
(delta-vs-baseline is None). This seeds a bullish baseline for a demo ticker, then runs the
pipeline over organic *bearish* posts — producing exactly one bounded, tighten-only proposal
in the review queue.

    python scripts/demo.py            # analyst/critic via deterministic MockLLMClient (offline, instant)
    python scripts/demo.py --live     # analyst/critic via real Gemini (needs GOOGLE_API_KEY in .env)

Then:
    quantlab proposals                # -> one pending proposal (inert)
    quantlab proposals --approve <id> # -> config 0.05 -> 0.035, versioned + audited
    quantlab proposals --rollback <ver>
"""
import argparse
from pathlib import Path

from quantlab.config import load_config
from quantlab.intelligence.agents import run_pipeline
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


def _make_llm(live: bool):
    """Real Gemini when --live (falls back to the mock if the SDK/key is unavailable)."""
    from quantlab.intelligence.llm import GeminiLLMClient, MockLLMClient
    if live:
        try:
            client = GeminiLLMClient()
            print("LLM: Gemini (live)")
            return client
        except Exception as e:
            print(f"[warn] Gemini unavailable ({e}); using MockLLMClient")
    else:
        print("LLM: MockLLMClient (offline, deterministic)")
    return MockLLMClient()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use real Gemini for analyst/critic")
    args = ap.parse_args()

    # load .env so --live picks up GOOGLE_API_KEY without manual export
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass

    cfg = load_config(_active())
    mem = SentimentMemory(RUNS / "intel.db")
    # 1) establish a BULLISH baseline over prior runs
    for d in ("2026-07-01", "2026-07-02", "2026-07-03"):
        mem.record(d, TICKER, 0.8, 5)
    # 2) today: organic BEARISH posts — substantive, varied, distinct authors, news-style (no hype/
    # spam cues), so even a live-Gemini critic judges them organic rather than a coordinated pump.
    seed = [(TICKER, f"analyst_{i}", t, "bear") for i, t in enumerate([
        "Downgrading ACME to Hold after weaker-than-expected quarterly guidance on the earnings call.",
        "ACME missed revenue consensus this quarter; management flagged softening end-market demand.",
        "Trimming my ACME estimates — rising input costs are squeezing margins into next year.",
        "ACME reportedly lost a large enterprise contract; near-term growth outlook looks weaker.",
        "Reducing ACME exposure after the disappointing results and cautious forward commentary."])]
    rep = run_pipeline([TICKER], [FixtureSource(seed=seed)], _make_llm(args.live), mem,
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
