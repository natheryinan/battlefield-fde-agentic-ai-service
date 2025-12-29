# fde/interfaces/core.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
import pandas as pd


# ========= ① 期权凸性空间 =========

@dataclass
class OptionSnapshot:
    """
    期权快照（给 ConvexityPersona 用）：
      - greeks: DataFrame，至少包含 ['underlying', 'gamma'] 列
    """
    greeks: Optional[pd.DataFrame] = None

# ========= ② 标的资产空间 =========

@dataclass
@dataclass
class MarketSnapshot:
    timestamp: pd.Timestamp
    prices: pd.Series
    volumes: Optional[pd.Series] = None
    orderbook: Any = None
    features: Optional[pd.DataFrame] = None
    options: Optional[OptionSnapshot] = None 




@dataclass
class PortfolioState:
    """
    PortfolioState
    ---------------
    组合 / 账户维度（给 Guardian + Engine 用）：

    - positions: 当前持仓，index = asset_id, value = quantity
    - cash / equity / pnl: 现金、净值、累计 PnL
    - greeks:   组合层面聚合后的 greeks（可选）
    - meta:     风控统计，如 drawdown, gross_leverage, net_exposure...
    """
    positions: pd.Series

    cash: float
    equity: float
    pnl: float

    greeks: Optional[pd.Series] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class RiskLimits:
    """
    RiskLimits
    ----------
    全局风控边界（Guardian 人格的配置）：

    - max_gross_leverage: 最大总杠杆
    - max_net_exposure:   最大净敞口
    - max_single_name_weight: 单一标的最大权重
    - max_drawdown:       最大回撤
    - var_limit / es_limit: VaR / ES 限制（可选）
    """
    max_gross_leverage: float
    max_net_exposure: float
    max_single_name_weight: float
    max_drawdown: float

    var_limit: Optional[float] = None
    es_limit: Optional[float] = None
    other: Optional[Dict[str, Any]] = None


# ========= ④ Persona 共享上下文 =========

@dataclass
class PersonaContext:
    """
    PersonaContext
    ---------------
    人格共享的上下文信息：

    - mode:   "live" / "paper" / "backtest" / "train"
    - step:   当前时间步（回测 / 训练时使用）
    - meta:   其他共享信息（如全局随机种子、当前 episode id 等）
    """
    mode: str = "live"
    step: int = 0
    meta: Optional[Dict[str, Any]] = None


@dataclass
class OptionSnapshot:
    
    greeks: Optional[pd.DataFrame] = None
