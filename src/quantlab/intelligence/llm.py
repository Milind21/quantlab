"""llm — the LLMClient seam. The whole agent pipeline runs against this interface, so it works
green offline with MockLLMClient and swaps to Gemini for the live demo.

`complete(system, user, schema_keys)` returns a parsed dict (strict-schema enforced by the
caller via guardrails.parse_strict). The mock is deterministic and rule-based — enough to
exercise orchestration, memory, guardrails, and eval without any API key or network.
"""
from __future__ import annotations

import json
import os
import re
from typing import Protocol


class LLMClient(Protocol):
    name: str
    def complete(self, system: str, user: str) -> str: ...


class MockLLMClient:
    """Deterministic stand-in. Reads ONLY the delimited untrusted block and scores sentiment by
    a tiny lexicon — never obeys instruction-like text (verifies the no-injection contract end to
    end). Returns JSON strings the agents parse via parse_strict."""
    name = "mock"
    BULL = {"moon", "buy", "bullish", "breakout", "beat", "surge", "upgrade", "rally", "long", "calls"}
    BEAR = {"crash", "sell", "bearish", "miss", "plunge", "downgrade", "dump", "short", "puts", "bankrupt"}

    def _untrusted(self, user: str) -> str:
        m = re.search(r"<untrusted_post>(.*?)</untrusted_post>", user, re.S)
        return (m.group(1) if m else user).lower()

    def complete(self, system: str, user: str) -> str:
        role = "analyst"
        if "critic" in system.lower():
            role = "critic"
        if role == "analyst":
            txt = self._untrusted(user)
            b = sum(w in txt for w in self.BULL)
            s = sum(w in txt for w in self.BEAR)
            sentiment = "bull" if b > s else "bear" if s > b else "neutral"
            conf = min(0.95, 0.5 + 0.1 * abs(b - s))
            themes = [t for t in ("earnings", "product", "macro", "litigation") if t in txt]
            return json.dumps({"sentiment": sentiment, "confidence": conf, "themes": themes})
        # critic: flag obvious coordination/echo cues present in the (sanitized) evidence text
        txt = self._untrusted(user)
        suspicious = any(k in txt for k in ("guaranteed", "to the moon", "🚀🚀", "pump", "must buy now"))
        return json.dumps({"manipulation_risk": "high" if suspicious else "low",
                           "organic": not suspicious})


class GeminiLLMClient:
    """Live Gemini via google-genai (swap-in for the demo). Requires GOOGLE_API_KEY.
    Imported lazily so the package + tests never depend on the SDK or a key."""
    name = "gemini"

    def __init__(self, model: str = "gemini-flash-latest"):
        from google import genai  # lazy; not a test/install dependency
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY not set")
        self._client = genai.Client(api_key=key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.models.generate_content(
            model=self._model,
            contents=[{"role": "user", "parts": [{"text": user}]}],
            config={"system_instruction": system, "response_mime_type": "application/json"},
        )
        return resp.text or "{}"
