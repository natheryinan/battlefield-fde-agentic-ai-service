from dataclasses import dataclass
from typing import Dict

from engine.personas.liquidity_guard import LiquiditySignal


@dataclass


class ReallocationRequired(RuntimeError):
    """
    Raised when a protection scaling operation results in NaN
    and the caller should trigger a reallocation / re-routing
    instead of blindly using a fallback numeric value.
    """
    pass


def _make_position_scale_fn(coefficient: float):
    """
    系数保护层：返回 f(raw_size) -> scaled_size

    If result becomes NaN, it means this path / persona is no
    longer numerically valid → trigger reallocation at router level.
    """
    def scale(raw_size: float) -> float:
        if not isinstance(raw_size, (int, float)):
            raise TypeError("raw_size must be numeric")

        scaled = float(raw_size) * float(coefficient)

        # NaN → do NOT coerce, force reroute / redistribute
        if not (scaled == scaled):  # NaN check
            raise ReallocationRequired(
                f"NaN in scaling: raw={raw_size}, coeff={coefficient} → reallocation required"
            )

        return scaled

    return scale

class ProtectionLayer:
    """
    Unified protection settings for a single persona.

    - position_scale: multiplicative cap on new position sizes
    - max_leverage: hard ceiling on leverage-like exposure
    - allow_new_risk: whether persona may open NEW risk at all
    - notes: human-readable explanation for logs / dashboards
    """
    position_scale: float
    max_leverage: float
    allow_new_risk: bool
    notes: str


@dataclass
class ProtectionBundle:
    """
    Protection layers for the three core roles:
    - alpha
    - guardian
    - router (config / sovereign router)
    """
    alpha: ProtectionLayer
    guardian: ProtectionLayer
    router: ProtectionLayer
    regime: str
    liquidity_score: float


class LiquidityProtectionFactory:
    """
    Map LiquiditySignal -> persona-specific protection layers.

    This is intentionally simple and monotonic:
    - As liquidity_score ↑, Alpha is throttled first.
    - Guardian becomes more dominant and conservative.
    - Router shifts routing away from risk-on personas.
    """

    def __init__(
        self,
        # knobs for how aggressive protection becomes
        normal_threshold: float = 0.25,
        caution_threshold: float = 0.55,
    ):
        self.normal_threshold = normal_threshold
        self.caution_threshold = caution_threshold

    def build(self, signal: LiquiditySignal) -> ProtectionBundle:
        s = signal.stability_score
        regime = signal.regime  # "normal" | "caution" | "fragile"

        if s < self.normal_threshold:
            # Layer 0 - Normal
            alpha = ProtectionLayer(
                position_scale=1.0,
                max_leverage=1.0,
                allow_new_risk=True,
                notes="Normal liquidity: Alpha allowed full playbook."
            )
            guardian = ProtectionLayer(
                position_scale=1.0,
                max_leverage=1.0,
                allow_new_risk=True,
                notes="Guardian passive/monitoring; standard checks only."
            )
            router = ProtectionLayer(
                position_scale=1.0,
                max_leverage=1.0,
                allow_new_risk=True,
                notes="Router neutral routing between personas."
            )

        elif s < self.caution_threshold:
            # Layer 1 - Caution
            alpha = ProtectionLayer(
                position_scale=0.6,
                max_leverage=0.7,
                allow_new_risk=True,
                notes="Caution: throttle new risk, shrink order sizes."
            )
            guardian = ProtectionLayer(
                position_scale=1.1,
                max_leverage=0.9,
                allow_new_risk=True,
                notes="Guardian elevated: tighten stops and limits."
            )
            router = ProtectionLayer(
                position_scale=0.8,
                max_leverage=0.8,
                allow_new_risk=True,
                notes="Router tilts flow away from aggressive strategies."
            )

        else:
            # Layer 2 - Fragile
            alpha = ProtectionLayer(
                position_scale=0.1,
                max_leverage=0.3,
                allow_new_risk=False,
                notes="Fragile: Alpha mostly frozen; only de-risking allowed."
            )
            guardian = ProtectionLayer(
                position_scale=1.3,
                max_leverage=0.7,
                allow_new_risk=True,
                notes="Guardian dominates: focus on unwind, hedge, capital preservation."
            )
            router = ProtectionLayer(
                position_scale=0.5,
                max_leverage=0.5,
                allow_new_risk=False,
                notes="Router reroutes flow to cash/hedges; block new speculative paths."
            )

        return ProtectionBundle(
            alpha=alpha,
            guardian=guardian,
            router=router,
            regime=regime,
            liquidity_score=s,
        )


def bundle_to_dict(bundle: ProtectionBundle) -> Dict[str, dict]:
    """
    Optional helper if you want a JSON- / YAML-friendly view for logging or config UIs.
    """
    return {
        "regime": bundle.regime,
        "liquidity_score": bundle.liquidity_score,
        "alpha": {
            "position_scale": bundle.alpha.position_scale,
            "max_leverage": bundle.alpha.max_leverage,
            "allow_new_risk": bundle.alpha.allow_new_risk,
            "notes": bundle.alpha.notes,
        },
        "guardian": {
            "position_scale": bundle.guardian.position_scale,
            "max_leverage": bundle.guardian.max_leverage,
            "allow_new_risk": bundle.guardian.allow_new_risk,
            "notes": bundle.guardian.notes,
        },
        "router": {
            "position_scale": bundle.router.position_scale,
            "max_leverage": bundle.router.max_leverage,
            "allow_new_risk": bundle.router.allow_new_risk,
            "notes": bundle.router.notes,
        },
    }
