"""mcp_server — exposes QuantLab's capabilities as MCP tools.

Any MCP client (Claude Desktop, an ADK agent, etc.) can now drive the multi-agent
market-intelligence pipeline and the human review queue as first-class tools. This is
"clever reuse of existing toolsets": each tool is a thin wrapper over code already used
by the CLI (run_pipeline, ProposalStore), so behavior is identical across surfaces.

The core work lives in plain functions (unit-testable); FastMCP just registers them as
tools. The LLM/order-path safety invariant is unchanged — `approve_proposal` is still the
only path that mutates config, and it re-validates against the frozen bounds.

Run:  python -m quantlab.mcp_server        (stdio transport)
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs"


def _active_config() -> Path:
    active = ROOT / "configs" / "active.yaml"
    if not active.exists():
        active.write_text((ROOT / "configs" / "base.yaml").read_text())
    return active


def _make_llm(live: bool):
    from .intelligence.llm import GeminiLLMClient, MockLLMClient
    if live:
        try:
            return GeminiLLMClient()
        except Exception:
            return MockLLMClient()
    return MockLLMClient()


# ---- plain, testable tool implementations ----
def tool_run_intel(watchlist: list[str], live: bool = False, run_date: str | None = None) -> dict:
    """Run the collector→analyst→critic→proposer pipeline for a watchlist.

    Returns per-ticker sentiment views, critic verdicts, and any bounded proposals
    (which are submitted to the review queue but remain INERT until a human approves).
    """
    from .config import load_config
    from .intelligence.agents import run_pipeline
    from .intelligence.memory import SentimentMemory
    from .intelligence.proposals import ProposalStore
    from .intelligence.sources.fixture import FixtureSource

    cfg = load_config(_active_config())
    rd = run_date or date.today().isoformat()
    expires = (date.fromisoformat(rd) + timedelta(days=7)).isoformat()
    mem = SentimentMemory(RUNS / "intel.db")
    rep = run_pipeline(watchlist, [FixtureSource()], _make_llm(live), mem,
                       cfg.model_dump(exclude={"tunable"}), cfg.tunable, rd,
                       since=0.0, expires_at=expires)
    store = ProposalStore(RUNS / "proposals", _active_config())
    proposals = []
    for p in rep.proposals:
        pid = store.submit(p)
        proposals.append({"id": pid, "param": p.param, "current": p.current,
                          "proposed": p.proposed, "confidence": p.confidence,
                          "rationale": p.rationale})
    return {
        "run_date": rd,
        "summary": rep.summary,
        "views": {tk: {"label": v.label, "score": round(v.score, 3),
                       "delta": v.delta, "themes": v.themes,
                       "organic": rep.critics[tk].organic}
                  for tk, v in rep.views.items()},
        "proposals": proposals,
    }


def tool_list_proposals() -> list[dict]:
    """List pending, human-review proposals (inert until approved)."""
    from .intelligence.proposals import ProposalStore
    store = ProposalStore(RUNS / "proposals", _active_config())
    return [{"id": pid, "param": p.param, "current": p.current, "proposed": p.proposed,
             "confidence": p.confidence, "rationale": p.rationale}
            for pid, p in store.list_pending()]


def tool_approve_proposal(proposal_id: str) -> dict:
    """Human gate: apply a proposal (re-validated against bounds), versioned + audited.
    This is the ONLY tool that mutates the active config."""
    from .intelligence.proposals import ProposalStore
    return ProposalStore(RUNS / "proposals", _active_config()).approve(proposal_id)


def tool_reject_proposal(proposal_id: str, reason: str = "human-rejected") -> dict:
    """Human gate: reject a proposal. Config is left untouched."""
    from .intelligence.proposals import ProposalStore
    return ProposalStore(RUNS / "proposals", _active_config()).reject(proposal_id, reason)


def build_server():
    """Construct the FastMCP server with QuantLab tools registered."""
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("quantlab")
    mcp.tool()(tool_run_intel)
    mcp.tool()(tool_list_proposals)
    mcp.tool()(tool_approve_proposal)
    mcp.tool()(tool_reject_proposal)
    return mcp


if __name__ == "__main__":
    build_server().run()
