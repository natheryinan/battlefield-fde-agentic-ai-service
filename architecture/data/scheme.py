# architecture/data/schemas.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import datetime as dt


# --- confacts helpers --------------------------------------------------------


def normalize_confacts(confacts_token: object) -> str:
    """
    Normalize legacy / mixed labels into FLEX-style confacts.
    Any legacy *_DOMAIN label is treated as a FLEX-space label.
    """
    if confacts_token is None:
        return ""

    token = str(confacts_token).strip().upper()

    # Generic legacy pattern: HEDGE_DOMAIN -> HEDGE_FLEX, etc.
    if token.endswith("_DOMAIN"):
        core = token[: -len("_DOMAIN")]
        if core:
            token = core

    replacements = {
        "HEDGE": "HEDGE_FLEX",
        "ALPHA": "ALPHA_FLEX_CORE",
        "LIQUIDITY": "LIQUIDITY_FLEX_ZONE",
        "CONVEXITY": "CONVEXITY_FLEX_BAND",
        "RISK": "RISK_FLEX_FIELD",
        "INDEX": "INDEX_FLEX",
    }

    return replacements.get(token, token)


# --- Static universe & instruments -------------------------------------------


@dataclass
class Instrument:
    """
    Canonical description of a tradable instrument in FDE.

    confacts = flexible conceptual classification
    (FLEX-space label, not traditional market taxonomy).
    """
    symbol: str
    confacts: str  # e.g. "ALPHA_FLEX_CORE", "HEDGE_FLEX"
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Backward compat: allow legacy 'asset_class' to still work
        legacy = getattr(self, "asset_class", None)

        if (not self.confacts) and legacy:
            self.confacts = str(legacy)

        self.confacts = normalize_confacts(self.confacts)


@dataclass
class UniverseDefinition:
    """
    Logical group of instruments to be tracked in a given experiment.
    """
    name: str
    instruments: List[Instrument]
    benchmark_symbol: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# --- Time-series state -------------------------------------------------------


@dataclass
class MarketSnapshot:
    """
    Point-in-time view of market state for the whole universe.
    """
    timestamp: dt.datetime
    prices: Dict[str, float]
    volumes: Dict[str, float] = field(default_factory=dict)
    volatility: Dict[str, float] = field(default_factory=dict)
    regime_label: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """
    Single-symbol position. Quantity sign encodes direction.
    """
    symbol: str
    quantity: float
    avg_price: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioState:
    """
    Portfolio snapshot compatible with all personas & Alpha.
    """
    timestamp: dt.datetime
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    equity: float = 0.0
    leverage: float = 0.0
    pnl: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


# --- Risk & constraints ------------------------------------------------------


@dataclass
class RiskLimits:
    """
    Hard risk guardrails, shared by all personas.
    """
    max_drawdown_pct: float
    max_leverage: float
    max_gross_exposure_pct: float
    max_single_name_pct: float
    max_turnover_pct_per_day: float = 100.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ViolationsEvent:
    """
    A single violations event recorded by the violations counter.
    """
    timestamp: dt.datetime
    code: str               # e.g. "MAX_LEVERAGE_BREACH"
    severity: str           # e.g. "WARN", "HARD_STOP"
    message: str
    source: str             # e.g. "GUARDIAN", "LIQUIDITY_SHIELD", "ALPHA"
    details: Dict[str, Any] = field(default_factory=dict)


# --- Orders & decisions ------------------------------------------------------


@dataclass
class Order:
    """
    Minimal architecture-level order representation.
    """
    symbol: str
    side: str          # "BUY" or "SELL"
    quantity: float
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    tag: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRequest:
    """
    Input to FDE core: what Alpha & personas see at each step.
    """
    snapshot: MarketSnapshot
    portfolio: PortfolioState
    risk_limits: RiskLimits
    universe: UniverseDefinition
    step_index: int
    mode: str = "BACKTEST"      # "BACKTEST" | "PAPER" | "LIVE"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResponse:
    """
    Output from FDE core: normalized decision surface for the step.
    """
    orders: List[Order]
    violations: List[ViolationsEvent] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    alpha_decision_id: Optional[str] = None
