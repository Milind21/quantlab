"""news_rss — publisher RSS / headline adapter (best-effort live). Lazy feedparser import."""
from __future__ import annotations


from ..schemas import Post

# A small set of finance RSS feeds (publisher feeds are ToS-clean for non-commercial use).
DEFAULT_FEEDS = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml"]


class NewsRSSSource:
    name = "news_rss"

    def __init__(self, feeds=None):
        self.feeds = feeds or DEFAULT_FEEDS

    def fetch(self, tickers: list[str], since: float) -> list[Post]:
        import feedparser  # lazy
        out = []
        for url in self.feeds:
            feed = feedparser.parse(url)
            for i, e in enumerate(feed.entries):
                title = getattr(e, "title", "")
                summary = getattr(e, "summary", "")
                body = f"{title} {summary}"
                for tk in tickers:
                    if tk in body:
                        out.append(Post(id=f"rss-{tk}-{i}", source="news_rss", ticker=tk,
                                        author="news", created_utc=since, text=body))
        return out
