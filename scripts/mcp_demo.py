"""mcp_demo.py — an MCP CLIENT that drives QuantLab's tools over the protocol.

Demonstrates "clever tool use": it launches the QuantLab MCP server (stdio), lists the tools it
exposes, then calls them — run_intel, list_proposals, and (if one is pending) approve_proposal —
exactly as Claude Desktop or an ADK agent would. Same safety guarantees on every surface:
approve is still the only path that changes config, and it re-validates against bounds.

    python scripts/demo.py            # (optional) stage a proposal first
    python scripts/mcp_demo.py        # client connects to the server and calls the tools
"""
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _text(result):
    """Extract the text payload from an MCP tool result."""
    parts = []
    for c in result.content:
        parts.append(getattr(c, "text", str(c)))
    return "\n".join(parts)


def _payload(result):
    """Return the tool's Python return value. FastMCP puts typed results in
    structuredContent['result']; fall back to parsing the text content."""
    sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict) and "result" in sc:
        return sc["result"]
    return json.loads(_text(result))


async def main():
    params = StdioServerParameters(command="python", args=["-m", "quantlab.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("=== MCP: tools exposed by the QuantLab server ===")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"  • {t.name}: {(t.description or '').splitlines()[0]}")

            print("\n=== MCP call: run_intel(watchlist=[NVDA, AAPL, XOM]) ===")
            r = await session.call_tool("tool_run_intel",
                                        {"watchlist": ["NVDA", "AAPL", "XOM"]})
            out = _payload(r)
            print("  summary:", out["summary"])

            print("\n=== MCP call: list_proposals() ===")
            r = await session.call_tool("tool_list_proposals", {})
            pending = _payload(r)
            print(f"  {len(pending)} pending proposal(s)")
            for p in pending:
                print(f"    [{p['id']}] {p['param']}: {p['current']} -> {p['proposed']}")

            if pending:
                pid = pending[0]["id"]
                print(f"\n=== MCP call: approve_proposal('{pid}')  (the human gate, via MCP) ===")
                r = await session.call_tool("tool_approve_proposal", {"proposal_id": pid})
                print(" ", _text(r))


if __name__ == "__main__":
    asyncio.run(main())
