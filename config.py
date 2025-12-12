# fde/config.py
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class DataConfig:
    """Market / alt-data config."""
    universe: list[str]
    bar_interval: str = "1min"
    # e.g. 'kdb', 'parquet', 's3', 'kafka'
    backend: str = "parquet"
    backend_params: Dict[str, Any] | None = None


@dataclass
class RiskConfig:
    """Portfolio / desk level risk limits."""
    max_gross_leverage: float = 4.0
    max_single_name_weight: float = 0.05
    max_drawdown_pct: float = 0.15
    max_daily_loss_pct: float = 0.04
    var_99_horizon_days: float = 1.0
    var_99_limit_pct: float = 0.05


@dataclass
class ExecutionConfig:
    """Execution / routing related config."""
    max_order_notional_pct_advr: float = 0.05
    max_order_spread_bps: float = 5.0
    prefer_passive: bool = True
    twap_seconds: int = 0  # 0 = immediate


@dataclass
class FDEConfig:
    """Top level config passed into the engine."""
    env: str = "backtest"  # 'backtest' | 'paper' | 'live'
    data: DataConfig | None = None
    risk: RiskConfig | None = None
    execution: ExecutionConfig | None = None
    extra: Dict[str, Any] | None = None
