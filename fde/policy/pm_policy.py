# fde/policy/pm_policy.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fde.interfaces.core import PortfolioState, PersonaContext


@dataclass
class PMProfile:
   
    regime: str
    alpha_weight: float
    convexity_weight: float
    guardian_risk_level: str
    max_gross_lev: float
    stress_score: float
    note: str = ""


def compute_stress_score(drawdown: float, vol: float) -> float:
    

    dd = float(drawdown)
    v = float(vol)

    dd_term = min(max(-dd / 0.30, 0.0), 1.0)

    
    v_term = min(max((v - 0.10) / (0.70 - 0.10), 0.0), 1.0)

    
    stress = 0.5 * dd_term + 0.5 * v_term
    return float(min(max(stress, 0.0), 1.0))


def choose_pm_profile(
    *,
    portfolio: PortfolioState,
    ctx: PersonaContext,
    vol: float = 0.0,
) -> PMProfile:
    """
    核心入口：给当前 (portfolio, ctx, vol) 选一条「宪法状态」。

    这里用 stress_score >= 0.87 作为 Guardian 直接接管的阈值。
    """

    dd = float(portfolio.meta.get("drawdown", 0.0))
    stress = compute_stress_score(dd, vol)

    # 你要的「0.870 起步就视为 stress_flag」
    STRESS_HARD = 0.87
    STRESS_MED  = 0.45

    stress_flag = stress >= STRESS_HARD

    if stress_flag:
        # 最高戒备：GUARDIAN 直接一票否决
        return PMProfile(
            regime="GUARDIAN_BOSS",
            alpha_weight=0.0,
            convexity_weight=-1.2,      # Universe Gamma 全力拦截
            guardian_risk_level="MAX_DEFENSE",
            max_gross_lev=0.7,          # 杠杆上限压得很低
            stress_score=stress,
            note=f"Stress HARD (dd={dd:.2%}, vol={vol:.2f}) → Guardian 完全接管",
        )

    if stress >= STRESS_MED:
        # 过渡态：Balanced，不是“多说一点”，而是仍然 Guardian 掌权，
        # 只是允许 Alpha 参与一部分。
        return PMProfile(
            regime="BALANCED_COUNCIL",
            alpha_weight=0.6,           # Alpha 有发言权，但不是帝王
            convexity_weight=-0.4,      # 仍然有明显的 Gamma 抑制
            guardian_risk_level="ELEVATED",
            max_gross_lev=1.0,
            stress_score=stress,
            note=f"Balanced council (dd={dd:.2%}, vol={vol:.2f}) → 议会制，共同决策",
        )

    # 默认：一切正常，允许 Alpha 驾驶，但 Guardian 永远在。
    return PMProfile(
        regime="ALPHA_DRIVE",
        alpha_weight=1.0,
        convexity_weight=-0.2,          # 轻微宇宙 Gamma 约束
        guardian_risk_level="NORMAL",
        max_gross_lev=1.4,
        stress_score=stress,
        note=f"Alpha-drive (dd={dd:.2%}, vol={vol:.2f}) → 守门人在后排看着",
    )
