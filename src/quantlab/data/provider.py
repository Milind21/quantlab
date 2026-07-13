"""DataProvider port. Adapters (yfinance now, Alpaca later) implement this Protocol.

The pure core never imports a concrete provider — only this interface.
"""
from __future__ import annotations

from typing import Protocol

import pandas as pd


class DataProvider(Protocol):
    def get_universe(self, as_of: str | None = None) -> list[str]: ...
    def get_ohlcv(self, tickers: list[str], start: str, end: str | None = None
                  ) -> dict[str, pd.DataFrame]: ...
