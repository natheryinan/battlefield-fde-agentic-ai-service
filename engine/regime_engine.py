"""
Market Regime Engine (Structured)
---------------------------------
A structured representation of market state + a regime engine that
scores current conditions and emits persona-ready constraints.

Core ideas:
- No single metric is "the ruler"
- Vol, liquidity, flow, and stress are separate objects
- Engine returns a RegimeAssessment object for personas/routers
"""

from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np


# === State Objects ======================================================

@dataclass
class VolatilityState:
    realized: float                  # observed std / variability
    trend: float                     # slope or momentum of vol
    forecast: Optional[float] = None # optional model-implied vol


@dataclass
class LiquidityState:
    """
    Microstructure-style liquidity.
    depth:        order book depth or volume at best levels
    spread:       bid-ask spread (absolute or bps)
    impact_cost:  estimated price impact per unit notional
    elasticity:   how much price can stretch before books snap
    forecast_fragility:
        optional model-implied fragility scalar to blend with realized
    """
    depth: float
    spread: float
    impact_cost: float
    elasticity: float
    forecast_fragility: Optional[float] = None


@dataclass
class FlowState:
    """
    Order flow and crowding.
    pressure:         buy-sell imbalance [-1, 1]
    net_inflow_ratio: net capital inflow vs baseline
    crowding_index:   how crowded positions are (0-1+)
    forecast_tension:
        optional model-implied flow tension scalar
    """
    pressure: float
    net_inflow_ratio: float
    crowding_index: float
    forecast_tension: Optional[float] = None


@dataclass
class StressState:
    """
    Slow structural stress, not tick noise.
    drawdown:        rolling peak-to-trough
    recovery_speed:  how quickly drawdowns heal
    tail_risk_index: kurtosis / jump proxy
    forecast_stress:
        optional model-implied structural stress scalar
    """
    drawdown: float
    recovery_speed: float
    tail_risk_index: float
    forecast_stress: Optional[float] = None


@dataclass
class MarketState:
    """
    Full snapshot of the market from the regime engine's POV.
    """
    volatility: VolatilityState
    liquidity: LiquidityState
    flow: FlowState
    stress: StressState


# === Regime Assessment ==================================================

@dataclass
class RegimeAssessment:
    """
    Output object for personas / routers.
    """
    score: float
    label: str
    band: int                      # 0 = calm ... 3 = critical

    # Hard constraints (for router / risk layer)
    max_leverage: float
    max_position_change: float     # allowed position change per step
    max_gross_shift: float         # allowed portfolio gross shift

    # Optional hints for personas (they can ignore)
    persona_guidance: Dict[str, str]


# === Regime Engine ======================================================

class RegimeEngine:

    def __init__(
        self,
        vol_elasticity_baseline: float = 1.0,
        shock_escalation_strength: float = 2.0,   # keeps old name for config compatibility
        liquidity_fragility_weight: float = 1.4,
        flow_crowding_weight: float = 1.2,
        tail_risk_weight: float = 1.6,
    ):
        self.vol_elasticity_baseline = vol_elasticity_baseline
        self.shock_escalation_strength = shock_escalation_strength
        self.liquidity_fragility_weight = liquidity_fragility_weight
        self.flow_crowding_weight = flow_crowding_weight
        self.tail_risk_weight = tail_risk_weight

    # ----- internal building blocks ------------------------------------

    def _elastic_vol_intensity(self, v: VolatilityState):
        realized = max(v.realized, 0.0)
        trend = max(v.trend, 0.0)

        base = realized * self.vol_elasticity_baseline
        reinforcement = trend ** 1.25

        if v.forecast is not None:
            base = 0.7 * base + 0.3 * v.forecast

        return base + reinforcement

    def _liquidity_fragility(self, l: LiquidityState):
        """
        Thin books + wide spreads + high impact cost -> fragility.
        Elasticity tempers the penalty. Optional forecast_fragility
        lets a higher model layer tilt the result.
        """
        depth_term = (1.0 / max(l.depth, 1e-6)) ** 0.6
        spread_term = l.spread
        impact_term = l.impact_cost ** 0.9
        elasticity_cushion = 1.0 / max(l.elasticity, 1e-3)

        realized_fragility = (depth_term + spread_term + impact_term) * elasticity_cushion
        fragility = self.liquidity_fragility_weight * realized_fragility

        if l.forecast_fragility is not None:
            fragility = 0.7 * fragility + 0.3 * l.forecast_fragility

        return fragility

    def _flow_tension(self, f: FlowState):
        pressure_term = abs(f.pressure) ** 1.1
        inflow_term = max(f.net_inflow_ratio, 0.0) ** 0.7
        crowding_term = f.crowding_index ** 1.2

        realized_tension = pressure_term + inflow_term + crowding_term
        tension = self.flow_crowding_weight * realized_tension

        if f.forecast_tension is not None:
            tension = 0.7 * tension + 0.3 * f.forecast_tension

        return tension

    def _structural_stress_load(self, s: StressState):
        """
        Structural stress load from drawdown + slow recovery + tails.
        This is a slow pressure metric, not a single crash event.
        """
        drawdown_term = s.drawdown ** 1.2
        slow_heal_penalty = (1.0 / max(s.recovery_speed, 1e-3)) ** 0.5
        tail_term = self.tail_risk_weight * s.tail_risk_index ** 1.3

        realized_stress = drawdown_term + slow_heal_penalty + tail_term
        structural_load = self.shock_escalation_strength * realized_stress

        if s.forecast_stress is not None:
            structural_load = 0.7 * structural_load + 0.3 * s.forecast_stress

        return structural_load

    # ----- public interface --------------------------------------------

    def evaluate(self, m: MarketState) -> RegimeAssessment:
        vol_part = self._elastic_vol_intensity(m.volatility)
        liq_part = self._liquidity_fragility(m.liquidity)
        flow_part = self._flow_tension(m.flow)
        stress_part = self._structural_stress_load(m.stress)

        score = float(vol_part + liq_part + flow_part + stress_part)
        band, label = self._label(score)
        max_leverage, max_pos_change, max_gross_shift = self._constraints_from_band(band)

        persona_guidance = {
            "ALPHA": self._alpha_guidance(band),
            "GUARDIAN": self._guardian_guidance(band),
            "LIQUIDITY": self._liquidity_guidance(band),
        }

        return RegimeAssessment(
            score=score,
            label=label,
            band=band,
            max_leverage=max_leverage,
            max_position_change=max_pos_change,
            max_gross_shift=max_gross_shift,
            persona_guidance=persona_guidance,
        )

    # ----- helper mappings ---------------------------------------------

    def _label(self, score: float):
        if score < 1.2:
            return 0, "Calm / Mean-Reverting"
        if score < 2.5:
            return 1, "Tense / Expanding Risk"
        if score < 4.0:
            return 2, "Fragile / Shock-Sensitive"
        return 3, "Critical — Crash Cascade Zone"

    def _constraints_from_band(self, band:_
