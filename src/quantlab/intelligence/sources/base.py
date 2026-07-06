"""SentimentSource port. Adapters (reddit/stocktwits/news_rss/fixture) implement fetch().
All sources are subject to the allowlist + rate caps; their text is UNTRUSTED."""
from __future__ import annotations

from typing import Protocol

from ..schemas import Post


class SentimentSource(Protocol):
    name: str
    def fetch(self, tickers: list[str], since: float) -> list[Post]: ...
