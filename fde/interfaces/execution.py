
# fde/interfaces/execution.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Dict, Any

import pandas as pd


@dataclass
class Order:
    symbol: str
    side: str          # 'BUY' or 'SELL'
    qty: float
    limit_price: float | None = None
    meta: Dict[str, Any] | None = None


@dataclass
class ExecutionReport:
    timestamp: datetime
    fills: pd.DataFrame         # rows: fills
    remaining: pd.DataFrame     # rows: open / canceled orders
    meta: Dict[str, Any] | None = None


class ExecutionInterface(Protocol):
    """Abstract OMS / EMS / router."""

    def send_orders(self, orders: list[Order]) -> ExecutionReport:
        ...

    def cancel_all(self) -> None:
        ...

    def get_open_orders(self) -> pd.DataFrame:
        ...
