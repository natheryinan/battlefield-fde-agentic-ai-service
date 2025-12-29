# fde/personas/guardian.py
from __future__ import annotations

import numpy as np
import pandas as pd

from fde.personas.base import BasePersona
from fde.interfaces.core import MarketSnapshot, PortfolioState, PersonaContext
from fde.policy.pm_policy import choose_pm_profile


class GuardianPersona(BasePersona):
    

    name = "FDE-GUARDIAN"
    description = "Supreme risk governor driven strictly by PM Constitution."

    def __init__(self, config=None):
        super().__init__(config or {})

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> pd.Series:
        # === 1️⃣ 向宪法请示当前 PM 状态 ===
        vol = float(portfolio.meta.get("vol", 0.0))
        profile = choose_pm_profile(
            portfolio=portfolio,
            ctx=ctx,
            vol=vol,
        )

        max_gross_lev = float(profile.max_gross_lev)

        # === 2️⃣ 计算当前组合的 gross leverage ===
        abs_positions = np.abs(portfolio.positions.values)
        gross_exposure = float(abs_positions.sum())
        equity = max(float(portfolio.equity), 1e-8)

        gross_lev = gross_exposure / equity

        # === 3️⃣ Guardian 的核心裁决公式 ===
        # 允许的杠杆 / 实际杠杆 → 风险缩放
        risk_weight = np.clip(
            max_gross_lev / max(gross_lev, 1e-6),
            0.0,
            1.0,
        )

        # === 4️⃣ Debug 输出（非常重要，给人类看的） ===
        print("\n--- GUARDIAN (SUPREME) DEBUG ---")
        print(f"regime            : {profile.regime}")
        print(f"stress_score      : {profile.stress_score:.3f}")
        print(f"guardian_level    : {profile.guardian_risk_level}")
        print(f"note              : {profile.note}")
        print(f"max_gross_lev     : {max_gross_lev}")
        print(f"gross_exposure    : {gross_exposure}")
        print(f"gross_leverage    : {gross_lev}")
        print(f"risk_weight       : {risk_weight}")
        print("--------------------------------\n")

        # === 5️⃣ 输出：对齐资产的一条统一 scaling ===
        return pd.Series(
            risk_weight,
            index=snapshot.prices.index,
            name="guardian_weight",
        )
