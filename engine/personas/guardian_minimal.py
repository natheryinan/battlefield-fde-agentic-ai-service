from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import math


@dataclass
class Observation:
    """
    Minimal, truthful market state for GuardianMinimal.

    price_span:
        - signed stretch of price relative to prior state
        - negative / positive only describe direction
        - the raw number is just a metric fed into the risk function

    market_elasticity:
        - how much movement the market can absorb
        - higher = softer / more resilient
        - lower = stiff / fragile
    """
    timestamp: datetime
    price: float
    price_span: float         # signed metric of movement (not itself the ruler)
    market_elasticity: float  # 0–1, higher = more resilient
    extra: Dict[str, Any]


@dataclass
class GuardianThresholds:
    """
    Core idea:

    Risk is not 'span alone'.
    Risk emerges from how span interacts with the market's ability
    to absorb it (elasticity).

    Intuition:
        - small span in a soft market → low effective shock
        - same span in a rigid market → high effective shock
    """
    span_comfort: float = 0.02        # comfortable movement scale (metric)
    elasticity_floor: float = 0.25    # below this → market is structurally fragile
    crash_span: float = 0.25          # movement scale where, if elasticity is weak, it's crisis-like


@dataclass
class GuardianAssessment:
    regime: str              # "NORMAL" / "STRESSED" / "CRASH"
    severity: float          # 0–1
    reasons: Dict[str, float]
    timestamp: datetime


class GuardianMinimal:
    """
    Minimal Guardian based on interaction between:

      • price_span  (行情走了多远)  — a metric
      • market_elasticity (市场能不能接住) — the medium

    Risk is a function of both, not just a ruler applied to span.
    """

    def __init__(self, thresholds: GuardianThresholds | None = None):
        self.t = thresholds or GuardianThresholds()

    def assess(self, obs: Observation) -> GuardianAssessment:
        t = self.t
        reasons: Dict[str, float] = {}

        # --- span metric (we care about size for shock, direction is carried in extra if needed) ---
        span_mag = abs(obs.price_span)

        # --- elasticity as the medium ---
        elasticity = max(obs.market_elasticity, 1e-6)  # avoid divide-by-zero
        elasticity_inverse = 1.0 / elasticity

        # effective_shock = metric(span) filtered through medium(elasticity)
        effective_shock = span_mag * elasticity_inverse
        reasons["effective_shock"] = effective_shock

        # how far this span metric is beyond the comfort scale
        span_ratio = max(0.0, span_mag / t.span_comfort - 1.0)
        if span_ratio > 0:
            reasons["span_metric_excess"] = span_ratio

        # rigidity penalty if the medium itself is weak
        if elasticity <= t.elasticity_floor:
            rigidity = (t.elasticity_floor - elasticity) / t.elasticicity_floor
            reasons["elasticity_fragility"] = rigidity

        # aggregate severity (smooth, bounded)
        raw = sum(reasons.values())
        severity = 0.0 if raw <= 0 else 1.0 - math.exp(-raw)

        # regime logic: driven by interaction, not span alone
        if severity == 0.0:
            regime = "NORMAL"
        elif span_mag >= t.crash_span and elasticity <= t.elasticity_floor:
            # big move + weak medium → full CRASH
            regime = "CRASH"
            severity = max(severity, 0.95)
        elif elasticity <= t.elasticity_floor:
            # medium itself is fragile → at least STRESSED
            regime = "STRESSED"
        elif span_mag >= t.crash_span:
            # big move but medium still okay → can still be treated as STRESSED/near-crash
            regime = "STRESSED"
        else:
            regime = "STRESSED" if severity > 0 else "NORMAL"

        return GuardianAssessment(
            regime=regime,
            severity=severity,
            reasons=reasons,
            timestamp=obs.timestamp,
        )
