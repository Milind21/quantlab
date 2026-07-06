"""memory — rolling sentiment store + per-ticker baselines (SQLite).

The analyst's signal is the DELTA vs a ticker's own rolling baseline (a sudden swing is the
news; raw bullishness is uninformative). This store persists per-run per-ticker sentiment scores
and computes the baseline over prior runs. Pure stdlib sqlite3; path injected (no global clock).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sentiment_history (
    run_date TEXT NOT NULL,
    ticker   TEXT NOT NULL,
    score    REAL NOT NULL,   -- weighted mean in [-1, 1] (bull=+1, bear=-1)
    n_posts  INTEGER NOT NULL,
    PRIMARY KEY (run_date, ticker)
);
"""


class SentimentMemory:
    def __init__(self, db_path: str | Path):
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path)

    def record(self, run_date: str, ticker: str, score: float, n_posts: int) -> None:
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO sentiment_history VALUES (?,?,?,?)",
                      (run_date, ticker, float(score), int(n_posts)))

    def baseline(self, ticker: str, before_date: str, window: int = 20) -> float | None:
        """Mean score over up to `window` prior runs (strictly before `before_date`).
        None if no history yet (no baseline -> no delta -> no proposal)."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT score FROM sentiment_history WHERE ticker=? AND run_date<? "
                "ORDER BY run_date DESC LIMIT ?", (ticker, before_date, window)).fetchall()
        if not rows:
            return None
        vals = [r[0] for r in rows]
        return sum(vals) / len(vals)

    def delta(self, ticker: str, current_score: float, before_date: str,
              window: int = 20) -> float | None:
        base = self.baseline(ticker, before_date, window)
        return None if base is None else current_score - base

    def history(self, ticker: str) -> list[tuple[str, float, int]]:
        with self._conn() as c:
            return c.execute("SELECT run_date, score, n_posts FROM sentiment_history "
                             "WHERE ticker=? ORDER BY run_date", (ticker,)).fetchall()
