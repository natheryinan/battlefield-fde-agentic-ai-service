# fde/interfaces/market.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable, Dict, Any

import pandas as pd


@dataclass
class MarketSnapshot:
    """Single time-step snapshot of market state."""
    timestamp: datetime
    prices: pd.Series          # index: symbol
    volumes: pd.Series | None = None
    order_book: Dict[str, Any] | None = None  # optional microstructure
    features: pd.DataFrame | None = None      # factor/feature matrix


@runtime_checkable
class MarketDataInterface(Protocol):
    """Abstraction for live / historical data sources."""

    def get_snapshot(self, when: datetime) -> MarketSnapshot:
        """Return market snapshot at given timestamp (or closest prior)."""
        ...

    def get_history(
        self,
        start: datetime,
        end: datetime,
        fields: list[str] | None = None,
    ) -> pd.DataFrame:
        """Return panel-like history, index=(timestamp, symbol)."""
        ...

    def stream(self) -> Any:
        """
        Optional async / generator for live data streaming.
        yield MarketSnapshot objects.
        """
        ...
