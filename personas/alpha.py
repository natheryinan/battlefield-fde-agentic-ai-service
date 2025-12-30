from datetime import datetime
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from personas.base import BasePersona, MarketState
from personas.convexity import ConvexityPersona
from personas.liquidity import LiquidityPersona
from personas.guardian import GuardianPersona
from personas.regime import RegimePersona
from personas.macro import MacroPersona
from personas.anomaly import AnomalyPersona
from personas.firefighter import FirefighterPersona
from personas.kid import KidPersona

from engine.royal_legal import RoyalLegalOverlay, RoyalLegalConfig



@dataclass
class AlphaConfig:
    """
    ALPHA 的“大佬配置区”：
    - 所有 personas（含 guardian）在这里平行排布：
        enable_xxx: 是否启用
        weight_xxx: 该 persona 的影响权重（乘到 delta 上）
    """

    # guardian：看护 persona，执行层免疫瓶颈
    enable_guardian: bool = True
    weight_guardian: float = 1.0

    # 其他底层 personas
    enable_convexity: bool = True
    weight_convexity: float = 1.0

    enable_liquidity: bool = True
    weight_liquidity: float = 1.0

    enable_regime: bool = True
    weight_regime: float = 1.0

    enable_macro: bool = True
    weight_macro: float = 1.0

    enable_anomaly: bool = True
    weight_anomaly: float = 1.0

    enable_firefighter: bool = True
    weight_firefighter: float = 1.0

    enable_kid: bool = False
    weight_kid: float = 0.3  # kid 默认轻一些

    # ROYAL LEGAL 惩戒 + 违纪瓶颈配置
    royal_legal_config: RoyalLegalConfig = field(
        default_factory=lambda: RoyalLegalConfig(
            risk_soft=0.2,
            risk_medium=0.45,
            risk_hard=0.7,
            cut_low=0.0,
            cut_mid=0.65,
            cut_high=1.0,
            cut_max=1.0,
            sanction_flatten=True,
        )
    )





class AlphaPersona(BasePersona):
    # ... __init__ 同前面的版本 ...

    def act(self, state: MarketState) -> Dict[str, float]:
        """
        Alpha 总入口：

          1) 从 state 里取时间戳，喂给 ROYAL LEGAL
          2) 向 ROYAL LEGAL 询问当前瓶颈系数 bottleneck(current_ts)
          3) 每个 persona:
                raw_delta = persona.act(state)
                weighted_delta = raw_delta * weight_xxx
                若是“加风险”且 非 guardian → 再乘 bottleneck
          4) 聚合所有缩放后的 delta
          5) 用 ROYAL LEGAL 对聚合结果做惩戒式截断（砍仓 / 平仓）
        """
        positions: Dict[str, float] = getattr(state, "positions", {}) or {}

        # 取时间戳（和 RoyalLegalOverlay 里的逻辑保持一致）
        raw_ts = getattr(state, "timestamp", None)
        if raw_ts is None:
            raw_ts = getattr(state, "time", None)

        if isinstance(raw_ts, datetime):
            current_ts: Optional[float] = raw_ts.timestamp()
        elif raw_ts is None:
            current_ts = None
        else:
            try:
                current_ts = float(raw_ts)
            except (TypeError, ValueError):
                current_ts = None

        # 1) 违纪瓶颈（带惩戒 end time）
        bottleneck = self._royal_legal.current_bottleneck_factor(current_ts=current_ts)

        proposals: Dict[str, Dict[str, float]] = {}

        for name, persona in self._personas.items():
            raw = persona.act(state)
            weight = self._weights.get(name, 1.0)

            scaled: Dict[str, float] = {}

            for sym, delta in raw.items():
                # 先乘 persona 自身权重
                delta_w = delta * weight

                pos = positions.get(sym, 0.0)
                new_pos = pos + delta_w
                increasing_risk = abs(new_pos) > abs(pos)

                if name == "guardian":
                    # guardian：配置层统一管理，执行层不受瓶颈限制
                    scaled[sym] = delta_w
                elif increasing_risk and bottleneck < 1.0:
                    # 非 guardian 且在加风险 → 被瓶颈压缩
                    scaled[sym] = delta_w * bottleneck
                else:
                    # 减仓 / 对冲 → 不限流
                    scaled[sym] = delta_w

            proposals[name] = scaled

        # 聚合 + 最终惩戒截断不变
        aggregated: Dict[str, float] = {}
        for action in proposals.values():
            for symbol, delta in action.items():
                aggregated[symbol] = aggregated.get(symbol, 0.0) + delta

        final_delta = self._royal_legal.apply(state, aggregated)
        return final_delta

