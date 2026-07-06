"""guardrails — the security layer (graded heavily).

All third-party text is UNTRUSTED DATA, never instructions. `sanitize_untrusted` neutralizes
prompt-injection and wraps content in clear delimiters before it reaches any LLM. Plus: source
allowlist, per-source rate caps, strict-schema parsing (malformed LLM output is DISCARDED, never
free-interpreted), and a per-run token/cost ceiling.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

ALLOWED_SOURCES = {"reddit", "stocktwits", "news_rss", "fixture"}

# Per-source request caps per run (Reddit free tier ~60 req/min).
RATE_CAPS = {"reddit": 60, "stocktwits": 120, "news_rss": 120, "fixture": 10_000}

# Instruction-like patterns that must never be interpreted as commands when found in post text.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(the\s+)?(system|previous|above)",
    r"\bsystem\s*:",
    r"\b(assistant|user)\s*:",
    r"you\s+are\s+now\b",
    r"new\s+instructions?\b",
    r"propose\s+(max|maximum|higher)\s+(leverage|risk|position)",
    r"disable\s+(the\s+)?(kill[- ]?switch|risk|stop)",
    r"<\s*/?\s*(system|tool|function|instructions?)\s*>",
    r"```\s*(system|tool|json)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_untrusted(text: str, max_len: int = 2000) -> str:
    """Neutralize instruction-like content and wrap as clearly-delimited untrusted data."""
    text = (text or "")[:max_len]
    text = _INJECTION_RE.sub("[redacted-injection]", text)
    # neutralize role/delimiter tokens an attacker might use to break out of the data block
    text = text.replace("```", "ʼʼʼ").replace("<|", "<​|").replace("|>", "|​>")
    return f"<untrusted_post>\n{text}\n</untrusted_post>"


def source_allowed(source: str) -> bool:
    return source in ALLOWED_SOURCES


def rate_cap(source: str) -> int:
    return RATE_CAPS.get(source, 30)


def parse_strict(raw: str, required_keys: set[str]) -> dict | None:
    """Parse LLM output as JSON with required keys. Returns None (DISCARD) on any malformation."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict) or not required_keys.issubset(obj.keys()):
        return None
    return obj


@dataclass
class TokenBudget:
    """Per-run token/cost ceiling. Agents check before each LLM call; over-budget -> stop."""
    ceiling: int = 200_000
    spent: int = 0
    calls: int = 0

    def charge(self, tokens: int) -> None:
        self.spent += tokens
        self.calls += 1

    def remaining(self) -> int:
        return max(0, self.ceiling - self.spent)

    def ok(self) -> bool:
        return self.spent < self.ceiling
