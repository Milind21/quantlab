"""YFinanceProvider — adjusted daily OHLCV via yfinance with per-ticker parquet caching.

Adapter (owns all network/disk I/O). Cache lives under data/cache/ (gitignored). A second call
for an already-cached (ticker, range) is a cache hit with no network. Columns normalized to
lower-case open/high/low/close/volume, DatetimeIndex named 'date'.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "cache"
UNIVERSE_CSV = ROOT / "configs" / "universe_small.csv"
_COLS = ["open", "high", "low", "close", "volume"]


class YFinanceProvider:
    def __init__(self, cache_dir: Path | str = CACHE):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)

    def get_universe(self, as_of: str | None = None) -> list[str]:
        df = pd.read_csv(UNIVERSE_CSV)
        return df["ticker"].tolist()

    def _cache_path(self, ticker: str) -> Path:
        return self.cache / f"{ticker}.parquet"

    def _load_cached(self, ticker: str) -> pd.DataFrame | None:
        p = self._cache_path(ticker)
        return pd.read_parquet(p) if p.exists() else None

    def _download(self, ticker: str, start: str, end: str | None) -> pd.DataFrame:
        import yfinance as yf
        raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if raw is None or len(raw) == 0:
            return pd.DataFrame(columns=_COLS)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.rename(columns=str.lower)[[c for c in _COLS if c.lower() in
                                             [x.lower() for x in raw.columns]]]
        raw.index.name = "date"
        return raw

    def get_ohlcv(self, tickers: list[str], start: str, end: str | None = None
                  ) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for t in tickers:
            cached = self._load_cached(t)
            if cached is not None and len(cached) and str(cached.index.min().date()) <= start:
                df = cached
            else:
                df = self._download(t, start, end)
                if len(df):
                    df.to_parquet(self._cache_path(t))
            if end is not None:
                df = df.loc[:end]
            out[t] = df.loc[start:] if len(df) else df
        return out
