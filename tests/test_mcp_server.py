"""MCP tools reuse the same core as the CLI and preserve the safety invariant:
run_intel submits inert proposals; approve is the only path that changes config."""
import shutil
import pytest
from quantlab import mcp_server as m


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    # redirect RUNS + active config into tmp so tests don't touch the real workspace
    monkeypatch.setattr(m, "RUNS", tmp_path / "runs")
    (tmp_path / "runs").mkdir()
    active = tmp_path / "active.yaml"
    shutil.copy("configs/base.yaml", active)
    monkeypatch.setattr(m, "_active_config", lambda: active)
    return active


def test_run_intel_offline_returns_views():
    out = m.tool_run_intel(["NVDA", "AAPL", "XOM"], live=False, run_date="2026-07-02")
    assert set(out["views"]) == {"NVDA", "AAPL", "XOM"}
    assert "summary" in out
    assert isinstance(out["proposals"], list)


def test_injection_ticker_yields_no_proposal():
    out = m.tool_run_intel(["XOM"], live=False, run_date="2026-07-02")
    assert out["proposals"] == []          # XOM fixture has an injection post -> inert


def test_server_registers_expected_tools():
    import asyncio
    srv = m.build_server()
    tools = asyncio.run(srv.list_tools())
    names = {t.name for t in tools}
    assert {"tool_run_intel", "tool_list_proposals", "tool_approve_proposal",
            "tool_reject_proposal"} <= names


def test_approve_is_only_config_mutation(tmp_path):
    import yaml
    from quantlab.intelligence.proposals import ProposalStore
    from quantlab.intelligence.schemas import ParamProposal
    active = m._active_config()
    store = ProposalStore(m.RUNS / "proposals", active)
    pid = store.submit(ParamProposal(param="risk.position_pct_cap", current=0.05, proposed=0.03,
                                     direction="tighten_only", rationale="bearish swing",
                                     confidence=0.8, expires_at="2026-12-31"))
    # listing does not mutate
    assert any(p["id"] == pid for p in m.tool_list_proposals())
    assert yaml.safe_load(active.read_text())["risk"]["position_pct_cap"] == 0.05
    # approve mutates (the only path)
    res = m.tool_approve_proposal(pid)
    assert res["applied"] is True
    assert yaml.safe_load(active.read_text())["risk"]["position_pct_cap"] == 0.03
