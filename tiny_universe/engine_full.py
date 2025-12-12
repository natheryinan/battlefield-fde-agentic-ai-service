
from toy_persona import (
    ToyAlphaPersona,
    ToyConvexityPersona,
    ToyGuardianPersona,
)
from toy_router import ToyEqualWeightRouter

from cosmic.wormhole import WormholeTensor
from cosmic.quantum_bridge import QuantumBridge



from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Protocol, Mapping, Optional
import numpy as np
import pandas as pd




@dataclass
class MarketSnapshot:
   
    prices: pd.Series
    features: Optional[p.DataFrame] = None
    timestamp: Any = None


@dataclass
class PortfolioState:
   
    positions: pd.Series  # index: asset_id, values: position size


@dataclass
class PersonaContext:
    
    mode: str = "demo"
    step: int = 0



class Persona(Protocol):
   
    name: str

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
        **kwargs: Any,
    ) -> pd.Series:
      


class SignalRouter(Protocol):
   

    def route(self, signals: Mapping[str, pd.Series]) -> pd.Series:
        ...




class FDEEngine:
    

    def __init__(self, personas, router, wormhole=None, qbridge=None):
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

        signals_after_wh = self.wormhole.transmit(signals_dict)

        final = self.qbridge.collapse(signals_after_wh)

    ) -> pd.Series:
        

       
        print("\n===== FDEEngine STEP DEBUG (toy) =====")
        print(f"Timestamp: {getattr(snapshot, 'timestamp', 'N/A')}")
        print(f"Context mode: {ctx.mode}, step: {ctx.step}")
        print(
            f"Num assets (prices): "
            f"{len(snapshot.prices) if snapshot.prices is not None else 'N/A'}"
        )
        print("=======================================")

        signals_dict: Dict[str, pd.Series] = {}

        signals_after_wh = self.wormhole.transmit(signals_dict)

        final = self.qbridge.collapse(signals_after_wh)

       
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

     
        final = self.router.route(signals_dict)

        print(">>> FDEEngine (toy) → Final signals (head):")
        print(final.head(10))
        print("===== END OF STEP (toy) =====\n")

        return final
    



if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    from toy_persona import (
        ToyAlphaPersona,
        ToyConvexityPersona,
        ToyGuardianPersona,
    )
    from toy_router import ToyEqualWeightRouter
    from cosmic.wormhole import WormholeTensor
    from cosmic.quantum_bridge import QuantumBridge

    # ------------------------------
    # 1. 构造资产列表
    # ------------------------------
    assets = ["CN_A1", "CN_A2", "CN_BANK", "US_SPY", "US_QQQ", "US_NVDA"]

    # ------------------------------
    # 2. 随机价格
    # ------------------------------
    rng = np.random.default_rng(2025)
    prices = pd.Series(
        rng.uniform(50, 200, size=len(assets)),
        index=assets,
        name="price",
    )

    # ------------------------------
    # 3. 构造持仓
    # ------------------------------
    positions = pd.Series(
        [200, 150, 300, -50, -30, -20],
        index=assets,
        name="position",
    )

    
    class Snapshot:
        def __init__(self, prices):
            self.prices = prices
            self.timestamp = "2025-12-09 00:00:00"

    class Portfolio:
        def __init__(self, positions):
            self.positions = positions

    class Context:
        def __init__(self):
            self.mode = "demo"
            self.step = 0

    snapshot = Snapshot(prices)
    portfolio = Portfolio(positions)
    ctx = Context()

  
    personas = {
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





class ToyAlphaPersona:
    
    name = "Toy-Alpha"

    def __init__(self, lookback: int = 60) -> None:
        self.lookback = lookback  

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        p
