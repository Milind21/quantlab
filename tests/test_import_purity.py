"""Pure-core modules must not import network / broker / clock-coupled libraries.
Adapters (data/*, cli, manifest's git subprocess) are exempt."""
import ast
from pathlib import Path

CORE = ["config.py", "indicators.py", "portfolio.py", "regime.py",
        "strategies/base.py", "strategies/trend_following.py", "strategies/mean_reversion.py",
        "backtest/vector.py", "report/metrics.py"]
FORBIDDEN = {"requests", "httpx", "urllib", "socket", "alpaca", "praw", "yfinance",
             "google", "backtrader", "datetime"}


def _imports(path):
    tree = ast.parse(Path(path).read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_core_is_pure():
    base = Path("src/quantlab")
    for f in CORE:
        bad = _imports(base / f) & FORBIDDEN
        assert not bad, f"{f} imports forbidden modules: {bad}"


def test_intelligence_never_imports_order_path():
    """The intelligence layer must not import the trade engine / broker / live order path."""
    import ast
    from pathlib import Path
    base = Path("src/quantlab/intelligence")
    forbidden = {"backtest", "broker", "live", "alpaca"}
    offenders = {}
    for f in base.rglob("*.py"):
        tree = ast.parse(f.read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                names.update(node.module.split("."))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    names.update(a.name.split("."))
        bad = names & forbidden
        if bad:
            offenders[str(f)] = bad
    assert not offenders, f"intelligence imports order-path modules: {offenders}"
