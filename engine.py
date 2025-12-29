# engine.py
from __future__ import annotations

from typing import Dict, Any
import pandas as pd

from fde.interfaces.core import MarketSnapshot, PortfolioState, PersonaContext


class FDEEngine:
    

    def __init__(self, personas: Dict[str, Any], router: Any) -> None:
        self.personas = personas
        self.router = router

    def step(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
        *,
        factors: Any,
    ) -> pd.Series:
      

        
        print("\n===== FDEEngine STEP DEBUG =====")
        print(f"Timestamp: {getattr(snapshot, 'timestamp', 'N/A')}")
        print(f"Context mode: {ctx.mode}, step: {ctx.step}")
        print(f"Num assets (prices): {len(snapshot.prices) if snapshot.prices is not None else 'N/A'}")
        print("=================================")

        signals_dict: Dict[str, pd.Series] = {}

        # --- Alpha Persona（必需） ---
        alpha_persona = self.personas.get("alpha")
        if alpha_persona is None:
            raise ValueError("FDEEngine: 'alpha' persona is required.")

        alpha_signals = alpha_persona.compute_signals(
            snapshot=snapshot,
            portfolio=portfolio,
            ctx=ctx,
            factors=factors,
        )
        signals_dict["alpha"] = alpha_signals

        
        convex_persona = self.personas.get("convexity")
        if convex_persona is not None:
            convex_signals = convex_persona.compute_signals(
                snapshot=snapshot,
                portfolio=portfolio,
                ctx=ctx,
            )
            signals_dict["convexity"] = convex_signals

        
        guardian_persona = self.personas.get("guardian")
        if guardian_persona is not None:
            guardian_signals = guardian_persona.compute_signals(
                snapshot=snapshot,
                portfolio=portfolio,
                ctx=ctx,
            )
            signals_dict["guardian"] = guardian_signals

        
        print("\n----- Personas Output Summary -----")
        for name, sig in signals_dict.items():
            print(f"[{name}] len={len(sig)}, head:")
            print(sig.head(10))
            print("--------------------------------")
        print("===================================\n")

        
        final = self.router.route(
    signals_dict,
    snapshot=snapshot,
    portfolio=portfolio,
    ctx=ctx,
)


        
        print(">>> FDEEngine → Final signals (head):")
        print(final.head(20))
        print("===== END OF STEP =====\n")

        return final
