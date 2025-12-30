# engine/fde.py
from typing import Dict, List

from personas.base import BasePersona, MarketState
from personas.alpha import AlphaPersona
from personas.convexity import ConvexityPersona
from personas.liquidity import LiquidityPersona
from personas.guardian import GuardianPersona
from personas.regime import RegimePersona
from personas.macro import MacroPersona
from personas.anomaly import AnomalyPersona
from personas.benchmark import BenchmarkPersona
from personas.compliance import CompliancePersona

from .royal_legal import RoyalLegalOverlay, RoyalLegalConfig


class FDEEngine:
    def __init__(
        self,
        personas: List[BasePersona] | None = None,
        royal_legal: RoyalLegalOverlay | None = None,
    ):
        # 正常 personas：只管“怎么动仓”
        self.personas = personas or [
            AlphaPersona(),
            ConvexityPersona(),
            LiquidityPersona(),
            GuardianPersona(),
            RegimePersona(),
            MacroPersona(),
            AnomalyPersona(),
            # benchmark / compliance usually configured with params
        ]

        # 惩戒式 ROYAL LEGAL：盖在最外层的大佬
        self.royal_legal = royal_legal or RoyalLegalOverlay(
            RoyalLegalConfig(
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

    def step(self, state: MarketState) -> Dict[str, float]:
        """
        1. 所有 personas 各自给出 delta（提案）
        2. 把这些 delta 按 symbol 相加 -> aggregated
        3. 交给 ROYAL LEGAL 做“惩戒截断”，得到最终 delta
        """
        # 1) persona proposals
        proposals: Dict[str, Dict[str, float]] = {}
        for p in self.personas:
            proposals[p.name] = p.act(state)

        # 2) 聚合所有 persona 的 delta
        aggregated: Dict[str, float] = {}
        for action in proposals.values():
            for symbol, delta in action.items():
                aggregated[symbol] = aggregated.get(symbol, 0.0) + delta

        # 3) 大佬出手：惩戒式 ROYAL LEGAL 截断
        if self.royal_legal is not None:
            aggregated = self.royal_legal.apply(state, aggregated)

        return aggregated
