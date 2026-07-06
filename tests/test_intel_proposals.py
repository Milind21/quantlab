import shutil
import yaml
from quantlab.intelligence.proposals import ProposalStore
from quantlab.intelligence.schemas import ParamProposal


def _active(tmp_path):
    src = "configs/base.yaml"
    dst = tmp_path / "active.yaml"
    shutil.copy(src, dst)
    return dst


def _proposal(proposed=0.035):
    return ParamProposal(param="risk.position_pct_cap", current=0.05, proposed=proposed,
                         direction="tighten_only", rationale="organic bearish swing",
                         confidence=0.8, expires_at="2026-12-31")


def test_submit_list_approve_mutates_config(tmp_path):
    active = _active(tmp_path)
    store = ProposalStore(tmp_path / "proposals", active)
    pid = store.submit(_proposal(0.035))
    assert len(store.list_pending()) == 1
    res = store.approve(pid)
    assert res["applied"] is True
    cfg = yaml.safe_load(active.read_text())
    assert cfg["risk"]["position_pct_cap"] == 0.035        # config actually changed
    assert len(store.list_pending()) == 0                  # moved to processed
    assert store.audit.exists()


def test_approve_revalidates_and_rejects_out_of_bounds(tmp_path):
    active = _active(tmp_path)
    store = ProposalStore(tmp_path / "proposals", active)
    # a proposal that LOOSENS (raises cap) — must be rejected at approval even if it reached the queue
    bad = ParamProposal(param="risk.position_pct_cap", current=0.05, proposed=0.09,
                        direction="tighten_only", rationale="sneaky", confidence=0.9,
                        expires_at="2026-12-31")
    pid = store.submit(bad)
    res = store.approve(pid)
    assert res["applied"] is False
    cfg = yaml.safe_load(active.read_text())
    assert cfg["risk"]["position_pct_cap"] == 0.05         # unchanged — bounds enforced at approval


def test_reject_leaves_config_untouched(tmp_path):
    active = _active(tmp_path)
    store = ProposalStore(tmp_path / "proposals", active)
    pid = store.submit(_proposal(0.03))
    store.reject(pid, "not convinced")
    cfg = yaml.safe_load(active.read_text())
    assert cfg["risk"]["position_pct_cap"] == 0.05
    assert len(store.list_pending()) == 0


def test_rollback_restores_prior_version(tmp_path):
    active = _active(tmp_path)
    store = ProposalStore(tmp_path / "proposals", active)
    res = store.approve(store.submit(_proposal(0.03)))
    assert yaml.safe_load(active.read_text())["risk"]["position_pct_cap"] == 0.03
    store.rollback(res["prev_version"])
    assert yaml.safe_load(active.read_text())["risk"]["position_pct_cap"] == 0.05  # reverted
