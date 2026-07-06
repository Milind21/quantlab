from quantlab.config import (
    load_config, parse_bounds, validate_proposal, get_param, run_id,
)

CFG_PATH = "configs/base.yaml"


def test_loads_and_has_defaults():
    cfg = load_config(CFG_PATH)
    assert cfg.risk.position_pct_cap == 0.05
    assert cfg.regime.sma_window == 200
    assert cfg.universe.benchmark == "SPY"


def test_bounds_parsed():
    cfg = load_config(CFG_PATH)
    b = parse_bounds(cfg.tunable)
    assert "risk.atr_stop_mult" in b
    assert b["risk.position_pct_cap"].direction == "tighten_only"


def test_validate_proposal_within_bounds():
    cfg = load_config(CFG_PATH)
    b = parse_bounds(cfg.tunable)["regime.band"]  # direction any
    assert validate_proposal(b, current=0.02, proposed=0.04)[0] is True
    assert validate_proposal(b, current=0.02, proposed=0.99)[0] is False  # > max


def test_validate_proposal_tighten_only():
    cfg = load_config(CFG_PATH)
    b = parse_bounds(cfg.tunable)["risk.position_pct_cap"]  # tighten_only
    # tightening (lower cap) allowed
    assert validate_proposal(b, current=0.05, proposed=0.03)[0] is True
    # loosening (raise cap) rejected even though within [min,max]
    ok, reason = validate_proposal(b, current=0.03, proposed=0.05)
    assert ok is False and "tighten_only" in reason


def test_atr_stop_tighten_means_lower():
    cfg = load_config(CFG_PATH)
    b = parse_bounds(cfg.tunable)["risk.atr_stop_mult"]
    assert validate_proposal(b, current=2.5, proposed=2.0)[0] is True   # tighter stop ok
    assert validate_proposal(b, current=2.5, proposed=3.0)[0] is False  # wider stop rejected


def test_get_param():
    cfg = load_config(CFG_PATH)
    assert get_param(cfg, "risk.atr_stop_mult") == 2.5


def test_run_id_deterministic_and_sensitive():
    cfg = load_config(CFG_PATH)
    assert run_id(cfg, "abc123") == run_id(cfg, "abc123")          # deterministic
    assert run_id(cfg, "abc123") != run_id(cfg, "def456")          # git sha matters
    cfg2 = cfg.model_copy(deep=True)
    cfg2.risk.max_positions = 10
    assert run_id(cfg, "abc123") != run_id(cfg2, "abc123")         # config change matters
