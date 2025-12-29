
from __future__ import annotations

import os
from typing import Dict, Any


from engine import FDEEngine as FullFDEEngine
from router import PersonaRouter


from fde.personas.alpha_multi import MultiFactorAlphaPersona
from fde.personas.convexity import ConvexityPersona

from tiny_universe.toy_engine import TinyEngine


def build_personas(config: Dict[str, Any] | None = None):
    cfg = config or {}
    return {
        "alpha": MultiFactorAlphaPersona(config=cfg),
        "convexity": ConvexityPersona(config=cfg),
        # "guardian": GuardianPersona(config=cfg),  # 你删了就别放
    }


def build_router(config: Dict[str, Any] | None = None):
    cfg = config or {}

    router = PersonaRouter()  # ✅ 不传任何参数

    # ✅ 如果你的 router 里有这个属性，就直接塞进去
    if hasattr(router, "convexity_weight"):
        router.convexity_weight = float(cfg.get("convexity_weight", -0.5))

    # ✅ 如果你未来实现了统一入口（推荐）
    if hasattr(router, "apply_pm_profile") and "pm_profile" in cfg:
        router.apply_pm_profile(cfg["pm_profile"])

    return router


def build_engine(config: Dict[str, Any] | None = None):
    use_decoy = os.getenv("FDE_PUBLIC_MODE", "0") == "1"

    personas = build_personas(config)
    router = build_router(config)

    if use_decoy:
        print(">>> [FDE PUBLIC MODE] Running Tiny Decoy Universe Engine")
        engine = TinyEngine(personas=personas, router=router)
        mode = "toy"
    else:
        print(">>> [FDE PRIVATE MODE] Running Full FDE Engine")
        engine = FullFDEEngine(personas=personas, router=router)
        mode = "full"

    return engine, mode, personas, router
