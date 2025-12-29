
# fde/interfaces/risk.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Dict, Any

import pandas as pd


@dataclass
class PortfolioState:
    """Current portfolio state."""
    positions: pd.Series        # index: symbol, value: quantity
    cash: float
    equity: float               # total equity value
    pnl_day: float              # intraday P&L
    meta: Dict[str, Any] | None = None


@dataclass
class RiskReport:
    """Output from risk engine at each step."""
    ok: bool
    reason: str | None = None
    limits: Dict[str, float] | None = None
    metrics: Dict[str, float] | None = None


class RiskEngineInterface(Protocol):
    """Abstraction for risk checking and risk-aware sizing."""

    def check(
        self,
        portfolio: PortfolioState,
        candidate_orders: pd.DataFrame,
    ) -> RiskReport:
        """
        candidate_orders: columns=[symbol, side, qty, notional,...].
        """
        ...

    def suggest_sizing(
        self,
        portfolio: PortfolioState,
        raw_signals: pd.Series,
    ) -> pd.Series:
        """
        Convert raw signals -> risk-aware target weights/quantities.
        """
        ...
