from quantlab.config import load_config
from quantlab.intelligence.agents import run_pipeline
from quantlab.intelligence.llm import MockLLMClient
from quantlab.intelligence.memory import SentimentMemory
from quantlab.intelligence.sources.fixture import FixtureSource


def _cfg():
    c = load_config("configs/base.yaml")
    return c.model_dump(exclude={"tunable"}), c.tunable


def test_pipeline_runs_and_summarizes(tmp_path):
    cfg, tunable = _cfg()
    mem = SentimentMemory(tmp_path / "intel.db")
    rep = run_pipeline(["NVDA", "AAPL", "XOM"], [FixtureSource()], MockLLMClient(), mem,
                       cfg, tunable, run_date="2026-06-10", since=0.0, expires_at="2026-06-17")
    assert set(rep.views) == {"NVDA", "AAPL", "XOM"}
    assert "NVDA" in rep.summary
    # NVDA fixture is bullish, AAPL bearish
    assert rep.views["NVDA"].label == "bull"
    assert rep.views["AAPL"].label == "bear"


def test_injection_post_never_yields_proposal(tmp_path):
    """The XOM fixture contains an injection post; it must NOT produce any proposal."""
    cfg, tunable = _cfg()
    mem = SentimentMemory(tmp_path / "intel.db")
    rep = run_pipeline(["XOM"], [FixtureSource()], MockLLMClient(), mem, cfg, tunable,
                       run_date="2026-06-10", since=0.0, expires_at="2026-06-17")
    assert rep.proposals == []                      # no baseline + injection inert -> nothing


def test_proposer_fires_only_on_organic_bearish_swing(tmp_path):
    """Seed a bullish baseline, then feed organic bearish posts -> a tightening proposal appears,
    bounded and tighten-only."""
    cfg, tunable = _cfg()
    mem = SentimentMemory(tmp_path / "intel.db")
    # establish a bullish baseline for ACME over prior runs
    for d in ("2026-06-01", "2026-06-02", "2026-06-03"):
        mem.record(d, "ACME", 0.8, 5)

    # organic bearish posts: many distinct authors, no dups, no manipulation cues
    seed = [("ACME", f"trader{i}", t, "bear") for i, t in enumerate([
        "ACME downgrade, weak guidance, bearish", "ACME misses, macro headwinds, sell",
        "ACME plunge on litigation, downgrade", "ACME bearish breakdown, dump",
        "ACME weak demand, sell rating"])]
    src = FixtureSource(seed=seed)
    rep = run_pipeline(["ACME"], [src], MockLLMClient(), mem, cfg, tunable,
                       run_date="2026-06-10", since=0.0, expires_at="2026-06-17")
    assert rep.views["ACME"].label == "bear"
    assert rep.views["ACME"].delta is not None and rep.views["ACME"].delta < -0.4
    assert len(rep.proposals) == 1
    p = rep.proposals[0]
    assert p.param == "risk.position_pct_cap"
    assert p.proposed < p.current                   # tightening only
    assert 0.01 <= p.proposed <= 0.05               # within bounds
    assert len(p.evidence) >= 1


def test_critic_flags_coordinated_and_blocks_proposal(tmp_path):
    """Same bearish swing but COORDINATED (one author, duplicate text, manipulation cue) ->
    critic marks suspect -> no proposal."""
    cfg, tunable = _cfg()
    mem = SentimentMemory(tmp_path / "intel.db")
    for d in ("2026-06-01", "2026-06-02", "2026-06-03"):
        mem.record(d, "ACME", 0.8, 5)
    dup = "ACME guaranteed crash, must buy now, pump it, sell sell sell"
    seed = [("ACME", "samebot", dup, "bear") for _ in range(5)]   # 1 author, identical text
    rep = run_pipeline(["ACME"], [FixtureSource(seed=seed)], MockLLMClient(), mem, cfg, tunable,
                       run_date="2026-06-10", since=0.0, expires_at="2026-06-17")
    assert rep.critics["ACME"].organic is False
    assert rep.proposals == []                      # suspect -> proposer blocked
