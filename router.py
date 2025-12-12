# fde/router.py
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from fde.interfaces.core import PortfolioState, PersonaContext, MarketSnapshot
from fde.policy.pm_policy import PMProfile, choose_pm_profile

"""
文明等级的尺度用

"""
class PersonaRouter:
    

    def __init__(self) -> None:
        self.last_profile: Optional[PMProfile] = None

    def _get_profile(
        self,
        *,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> PMProfile:
        # vol 先用 portfolio.meta["vol"]，后面你要接真实 vol 再升级
        vol = float(portfolio.meta.get("vol", 0.0))
        profile = choose_pm_profile(portfolio=portfolio, ctx=ctx, vol=vol)
        self.last_profile = profile
        return profile

    def route(
        self,
        signals: Dict[str, pd.Series],
        *,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> pd.Series:
        

        if "alpha" not in signals:
            raise ValueError("PersonaRouter.route: missing required 'alpha' signals.")

        alpha_sig = signals["alpha"]
        convex_sig = signals.get("convexity")
        guardian_scale = signals.get("guardian")

        # === 1) 宪法裁决 ===
        profile = self._get_profile(snapshot=snapshot, portfolio=portfolio, ctx=ctx)

        # === 2) 组合：alpha + convexity ===
        combo = alpha_sig * float(profile.alpha_weight)

        if convex_sig is not None:
            combo = combo + convex_sig * float(profile.convexity_weight)

        # === 3) Guardian scaling 作为“玉皇圣旨”乘子 ===
        if guardian_scale is not None:
            combo = combo * guardian_scale

        # === 4) Debug 输出（给人类看的） ===
        print("\n===== PersonaRouter (CONSTITUTION) DEBUG =====")
        print(f"regime         : {profile.regime}")
        print(f"stress_score   : {profile.stress_score:.3f}")
        print(f"risk_level     : {profile.guardian_risk_level}")
        print(f"alpha_weight   : {profile.alpha_weight}")
        print(f"convex_weight  : {profile.convexity_weight}")
        print(f"max_gross_lev  : {profile.max_gross_lev}")
        print(f"note           : {profile.note}")
        print("Signals combo (alpha / convexity / guardian / final):")

        df_dbg = pd.DataFrame(
            {
                "alpha": alpha_sig,
                "convexity": convex_sig if convex_sig is not None else 0.0,
                "guardian_scale": guardian_scale if guardian_scale is not None else 1.0,
                "final": combo,
            }
        )
        print(df_dbg.head(10))
        print("==============================================\n")

        return combo
