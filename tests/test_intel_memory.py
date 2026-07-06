from quantlab.intelligence.memory import SentimentMemory


def test_baseline_and_delta(tmp_path):
    m = SentimentMemory(tmp_path / "intel.db")
    assert m.baseline("NVDA", "2026-06-10") is None        # no history -> no baseline
    assert m.delta("NVDA", 0.8, "2026-06-10") is None
    m.record("2026-06-01", "NVDA", 0.1, 5)
    m.record("2026-06-02", "NVDA", 0.3, 6)
    base = m.baseline("NVDA", "2026-06-10")
    assert abs(base - 0.2) < 1e-9                            # mean of prior runs
    assert abs(m.delta("NVDA", 0.8, "2026-06-10") - 0.6) < 1e-9  # swing vs baseline
    # baseline excludes the current/future date
    assert m.baseline("NVDA", "2026-06-02") == 0.1


def test_upsert_and_history(tmp_path):
    m = SentimentMemory(tmp_path / "intel.db")
    m.record("2026-06-01", "AAPL", -0.2, 3)
    m.record("2026-06-01", "AAPL", -0.4, 4)   # same key -> replace
    h = m.history("AAPL")
    assert len(h) == 1 and abs(h[0][1] - (-0.4)) < 1e-9
