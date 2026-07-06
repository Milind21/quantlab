"""reddit — PRAW adapter (best-effort live). Lazy import so the package/tests never need praw.
Honors the per-source rate cap; non-commercial OAuth tier. Reads configured subreddits."""
from __future__ import annotations

import os

from ..guardrails import rate_cap
from ..schemas import Post

DEFAULT_SUBS = ["stocks", "wallstreetbets", "investing"]


class RedditSource:
    name = "reddit"

    def __init__(self, subreddits=None):
        self.subreddits = subreddits or DEFAULT_SUBS

    def _client(self):
        import praw  # lazy
        return praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.environ.get("REDDIT_USER_AGENT", "quantlab/0.1"),
        )

    def fetch(self, tickers: list[str], since: float) -> list[Post]:
        reddit = self._client()
        cap = rate_cap("reddit")
        out, n = [], 0
        for sub in self.subreddits:
            for post in reddit.subreddit(sub).new(limit=cap):
                if n >= cap:
                    break
                n += 1
                if post.created_utc < since:
                    continue
                body = f"{post.title} {getattr(post, 'selftext', '')}"
                for tk in tickers:
                    if f"${tk}" in body or f" {tk} " in f" {body} ":
                        out.append(Post(id=f"rd-{post.id}", source="reddit", ticker=tk,
                                        author=str(post.author), created_utc=post.created_utc,
                                        text=body))
        return out
