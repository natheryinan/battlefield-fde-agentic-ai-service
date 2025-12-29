
# pm_policy.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Any

from fde.interfaces.core import MarketSnapshot, PortfolioState, PersonaContext


RegimeName = Literal["ALPHA_BOSS", "CONVEXITY_BOSS", "GUARDIAN_BOSS", "BALANCED"]


@dataclass
class PMProfile:
    """仓位大佬宪法在这一拍的裁决"""
    regime: RegimeName          # 哪个大佬当班
    alpha_weight: float         # Router 给 alpha 的基础权重
    convexity_weight: float     # Router 给 convexity 的基础权重
    guardian_risk_level: str    # 文字版风险档位，比如 "MAX_DEFENSE"
    max_gross_lev: float        # Guardian 允许的最大 gross lev
    note: str = ""              # debug / 日志专用


def pick_pm_profile(
    snapshot: MarketSnapshot,
    portfolio: PortfolioState,
    ctx: PersonaContext,
) -> PMProfile:
    """
    大佬投票制：根据 drawdown / 波动 / 外部 stress flag，决定谁是老大。
    注意：**离散 regime**，不是线性插值。
    """
    dd = float(portfolio.meta.get("drawdown", 0.0))

    # 从 features 或 meta 里取一个简单波动 proxy（你以后可以换成真实 vol）
    if snapshot.features is not None:
        vol = float(snapshot.features.get("realized_vol", 0.2))
    else:
        vol = float(portfolio.meta.get("realized_vol", 0.2))

    stress_flag = bool(portfolio.meta.get("stress_flag", False))

    # === regime 判决 ===
    # 1) 极端情况：任何一票 stress / 大回撤 → 直接 GUARDIAN 当皇帝
    if stress_flag or dd < -0.25 or vol > 0.65:
        return PMProfile(
            regime="GUARDIAN_BOSS",
            alpha_weight=0.0,
            convexity_weight=-1.2,   # Universe Gamma 全力拦截
            guardian_risk_level="MAX_DEFENSE",
            max_gross_lev=0.7,
            note=f"Stress / deep DD (dd={dd:.2f}, vol={vol:.2f}) → Guardian 皇权模式",
        )

    # 2) 中度压力：convexity 当班，alpha 降权
    if dd < -0.15 or vol > 0.45:
        return PMProfile(
            regime="CONVEXITY_BOSS",
            alpha_weight=0.5,
            convexity_weight=-0.8,
            guardian_risk_level="DEFENSE",
            max_gross_lev=1.0,
            note=f"Medium risk (dd={dd:.2f}, vol={vol:.2f}) → Convexity 当班",
        )

    # 3) 一切平稳：alpha 当班，convexity 少说话
    if dd > -0.05 and vol < 0.35:
        return PMProfile(
            regime="ALPHA_BOSS",
            alpha_weight=1.0,
            convexity_weight=-0.2,
            guardian_risk_level="NORMAL",
            max_gross_lev=1.5,
            note=f"Calm regime (dd={dd:.2f}, vol={vol:.2f}) → Alpha 发号施令",
        )

    # 4) 其它情况：平衡委员会
    return PMProfile(
        regime="BALANCED",
        alpha_weight=0.8,
        convexity_weight=-0.5,
        guardian_risk_level="BALANCED",
        max_gross_lev=1.2,
        note=f"Mixed signals (dd={dd:.2f}, vol={vol:.2f}) → 平衡制衡模式",
    )


# Router 用：从 profile 里抽取 Router config
def router_config_from_profile(profile: PMProfile) -> Dict[str, Any]:
    return {
        "alpha_weight": profile.alpha_weight,
        "convexity_weight": profile.convexity_weight,
        # 以后你要再加别的人格权重，都从这走
    }


# Guardian 用：从 profile 里抽取 max gross lev
def guardian_max_lev_from_profile(profile: PMProfile) -> float:
    return profile.max_gross_lev
