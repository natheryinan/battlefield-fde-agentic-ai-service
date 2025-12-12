from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Protocol, Mapping, Optional

import pandas as pd

from .toy_persona import (
    ToyAlphaPersona,
    ToyConvexityPersona,
    ToyGuardianPersona,
)
from .toy_router import ToyEqualWeightRouter
from .cosmic.wormhole import WormholeTensor
from .cosmic.quantum_bridge import QuantumBridge


# =======================
# Dataclasses / Types
# =======================

@dataclass
class MarketSnapshot:
    """
    单期市场快照：
      - prices: 资产价格
      - features: 额外因子（可选）
      - timestamp: 任意时间戳信息
    """
    prices: pd.Series
    features: Optional[pd.DataFrame] = None
    timestamp: Any = None


@dataclass
class PortfolioState:
    """
    组合状态：
      - positions: 每个资产的持仓
    """
    positions: pd.Series  # index: asset_id, values: position size


@dataclass
class PersonaContext:
    """
    人格上下文：
      - mode: demo / live / backtest ...
      - step: 当前步数
    """
    mode: str = "demo"
    step: int = 0


class Persona(Protocol):
    """
    人格接口协议：
      - 必须有 name
      - 必须实现 compute_signals()
    """
    name: str

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
        **kwargs: Any,
    ) -> pd.Series:
        ...


class SignalRouter(Protocol):
    """
    Router 接口协议：
      - route: 输入 {persona_name: Series} 输出 1D Series
    """

    def route(self, signals: Mapping[str, pd.Series]) -> pd.Series:
        ...


# =======================
# FDE Engine (full toy)
# =======================

class FDEEngine:
    """
    Full Tiny-Universe FDE Engine (toy)
    -----------------------------------
    personas : dict[str, Persona]
    router   : SignalRouter
    wormhole : WormholeTensor  （高维传输）
    qbridge  : QuantumBridge    （坍缩 / 融合）
    """

    def __init__(
        self,
        personas: Dict[str, Persona],
        router: SignalRouter,
        wormhole: WormholeTensor | None = None,
        qbridge: QuantumBridge | None = None,
    ) -> None:
        self.personas = personas
        self.router = router
        self.wormhole = wormhole or WormholeTensor()
        self.qbridge = qbridge or QuantumBridge()

    def step(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
        *,
        factors: Any | None = None,
    ) -> pd.Series:
        """
        单步演化：
          1. 调用各人格 compute_signals()
          2. signals_dict → wormhole.transmit
          3. 传输后 → qbridge.collapse
          4. collapse 后 → router.route
        """

        print("\n===== FDEEngine STEP DEBUG (toy) =====")
        print(f"Timestamp: {getattr(snapshot, 'timestamp', 'N/A')}")
        print(f"Context mode: {ctx.mode}, step: {ctx.step}")
        print(
            f"Num assets (prices): "
            f"{len(snapshot.prices) if snapshot.prices is not None else 'N/A'}"
        )
        print("=======================================")

        # 1️⃣ 收集各人格信号
        signals_dict: Dict[str, pd.Series] = {}

        alpha_persona = self.personas.get("alpha")
        if alpha_persona is None:
            raise ValueError("FDEEngine (toy): 'alpha' persona is required for demo.")

        alpha_signals = alpha_persona.compute_signals(
            snapshot=snapshot,
            portfolio=portfolio,
            ctx=ctx,
            factors=factors,
        )
        signals_dict["alpha"] = alpha_signals

        for key in ("convexity", "guardian"):
            persona = self.personas.get(key)
            if persona is not None:
                sig = persona.compute_signals(
                    snapshot=snapshot,
                    portfolio=portfolio,
                    ctx=ctx,
                )
                signals_dict[key] = sig

        print("\n----- Personas Output Summary (toy) -----")
        for name, sig in signals_dict.items():
            print(f"[{name}] len={len(sig)}, head:")
            print(sig.head(5))
            print("------------------------------------")
        print("=========================================\n")

        # 2️⃣ wormhole 传输（高维变换）
        signals_after_wh = self.wormhole.transmit(signals_dict)

        # 3️⃣ quantum bridge 坍缩 / 融合
        collapsed = self.qbridge.collapse(signals_after_wh)

        # 4️⃣ Router 决策合成
        final = self.router.route(collapsed)

        print(">>> FDEEngine (toy) → Final signals (head):")
        print(final.head(10))
        print("===== END OF STEP (toy) =====\n")

        return final


# =======================
# __main__ Demo
# =======================

if __name__ == "__main__":
    import numpy as np

    # 1. 构造资产 & 随机价格
    assets = ["CN_A1", "CN_A2", "CN_BANK", "US_SPY", "US_QQQ", "US_NVDA"]
    rng = np.random.default_rng(2025)

    prices = pd.Series(
        rng.uniform(50, 200, size=len(assets)),
        index=assets,
        name="price",
    )

    positions = pd.Series(
        [200, 150, 300, -50, -30, -20],
        index=assets,
        name="position",
    )

    snapshot = MarketSnapshot(
        prices=prices,
        features=None,
        timestamp="2025-12-09 00:00:00",
    )
    portfolio = PortfolioState(positions=positions)
    ctx = PersonaContext(mode="demo", step=0)

    personas: Dict[str, Persona] = {
        "alpha": ToyAlphaPersona(),
        "convexity": ToyConvexityPersona(),
        "guardian": ToyGuardianPersona(),
    }
    router = ToyEqualWeightRouter()
    wormhole = WormholeTensor(curvature=0.618)
    qbridge = QuantumBridge(collapse_mode="mean")

    engine = FDEEngine(
        personas=personas,
        router=router,
        wormhole=wormhole,
        qbridge=qbridge,
    )

    final = engine.step(
        snapshot=snapshot,
        portfolio=portfolio,
        ctx=ctx,
        factors={"dummy": 1.0},
    )

    print("\n=== FINAL SIGNALS (tiny_universe) ===")
    print(final)
