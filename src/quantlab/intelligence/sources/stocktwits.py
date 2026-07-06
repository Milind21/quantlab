"""stocktwits — public symbol-stream adapter (best-effort live). Native bull/bear tags.
Lazy requests import; honors rate cap."""
from __future__ import annotations

from ..guardrails import rate_cap
from ..schemas import Post

API = "https://api.stocktwits.com/api/2/streams/symbol/{tk}.json"


class StockTwitsSource:
    name = "stocktwits"

    def fetch(self, tickers: list[str], since: float) -> list[Post]:
        import requests  # lazy
        out, cap = [], rate_cap("stocktwits")
        for tk in tickers[:cap]:
            try:
                r = requests.get(API.format(tk=tk), timeout=10)
                if r.status_code != 200:
                    continue
                for m in r.json().get("messages", []):
                    ent = (m.get("entities") or {}).get("sentiment") or {}
                    tag = {"Bullish": "bull", "Bearish": "bear"}.get(ent.get("basic"))
                    out.append(Post(id=f"st-{m['id']}", source="stocktwits", ticker=tk,
                                    author=str(m.get("user", {}).get("username", "anon")),
                                    created_utc=since, text=m.get("body", ""), native_tag=tag))
            except Exception:
                continue
        return out
