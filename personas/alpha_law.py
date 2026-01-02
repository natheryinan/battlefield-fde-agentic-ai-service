"""
Alpha Law
---------
Risk law wrapper for ALPHA persona.

- Alpha does NOT decide absolute hard caps (that's SovereignRouter).
- AlphaLaw instead shapes:
    - target risk span (0–1)
    - trade intensity
    - directional bias tolerance

Inputs:
- MarketState (environment structure)
- RegimeAssessment (sovereign view)
- Current covenant status for ALPHA (violations / cooldown flag)
"""

from dataclasses import dataclass
from typing import Optional

# Adjust these imports to your actual package paths
try:
    from engine.regime_engine import MarketState, RegimeAssessment, VolatilityState, StressState
except ImportError:  # type: ignore
    # minimal stubs so this file is syntactically valid if imported alone
    @dataclass
    class VolatilityState:
        realized: float
        trend: float
        forecast: Optional[float] = None

    @dataclass
    class StressState:
        drawdown: float
        recovery_speed: float
        tail_risk_index: float

    @dataclass
    class MarketState:
        volatility: VolatilityState
        stress: StressState

    @dataclass
    class RegimeAssessment:
        score: float
        band: int
        label: str


@dataclass
class AlphaLawConfig:
    """
    Parameters for Alpha's operating law.
    """
    base_span: float = 0.65        # default risk span in calm regimes
    min_span: float = 0.05         # floor
    max_span: float = 0.9          # ceiling

    vol_sensitivity: float = 1.1   # how strongly vol compresses span
    stress_sensitivity: float = 1.3

    cooldown_span: float = 0.0     # risk span when in cooldown
    max_trade_intensity: float = 1.0
    min_trade_intensity: float = 0.05


@dataclass
class AlphaRiskEnvelope:
    """
    Output of AlphaLaw: a soft envelope that lives
    inside SovereignRouter's hard corridor.
    """
    target_risk_span: float        # [0,1] scalar
    trade_intensity: float         # [0,1] frequency/size tilt
    directional_bias_limit: float  # [0,1] allowed net bias

    commentary: str                # human-readable line for logs


class AlphaLaw:

    def __init__(self, config: Optional[AlphaLawConfig] = None):
        self.config = config or AlphaLawConfig()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def compute_envelope(
        self,
        market_state: MarketState,
        assessment: RegimeAssessment,
        covenant_violations: int,
        under_cooldown: bool,
    ) -> AlphaRiskEnvelope:
        """
        Combine regime + structural stress + covenant status into
        a continuous risk envelope.
        """
        band = assessment.band
        v = market_state.volatility
        s = market_state.stress

        if under_cooldown:
            # Alpha stands down; blade sheathed.
            return AlphaRiskEnvelope(
                target_risk_span=self.config.cooldown_span,
                trade_intensity=self.config.min_trade_intensity,
                directional_bias_limit=0.0,
                commentary="Cooldown active; Alpha restricted to neutral hedging only.",
            )

        # 1) Base span from regime band
        span_from_band = self._span_from_band(band)

        # 2) Vol + structural stress compression
        span_after_vol = self._apply_volatility(span_from_band, v)
        span_after_stress = self._apply_stress(span_after_vol, s)

        # 3) Covenant penalty (if already violated once)
        span_after_covenant = self._apply_covenant_penalty(
            span_after_stress,
            covenant_violations,
        )

        # 4) Trade intensity & directional bias from final span + band
        trade_intensity = self._trade_intensity_from_span(span_after_covenant, band)
        bias_limit = self._directional_bias_limit(band, covenant_violations)

        commentary = (
            f"Band={band}, base_span={span_from_band:.3f}, "
            f"span_vol={span_after_vol:.3f}, span_stress={span_after_stress:.3f}, "
            f"span_final={span_after_covenant:.3f}, "
            f"violations={covenant_violations}"
        )

        return AlphaRiskEnvelope(
            target_risk_span=span_after_covenant,
            trade_intensity=trade_intensity,
            directional_bias_limit=bias_limit,
            commentary=commentary,
        )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _span_from_band(self, band: int) -> float:
        """
        Map regime band -> coarse risk span.
        0: widest, 3: narrowest.
        """
        if band == 0:
            return self.config.base_span
        if band == 1:
            return 0.5 * self.config.base_span
        if band == 2:
            return 0.3 * self.config.base_span
        # band 3 (critical)
        return 0.15 * self.config.base_span

    def _apply_volatility(self, span: float, v: VolatilityState) -> float:
        """
        Vol compression: higher realized + trend => smaller span.
        """
        vol_level = max(v.realized, 0.0)
        vol_trend = max(v.trend, 0.0)

        # smooth composite volatility
        composite_vol = vol_level + 0.5 * vol_trend

        factor = 1.0 / (1.0 + self.config.vol_sensitivity * composite_vol)
        return span * factor

    def _apply_stress(self, span: float, s: StressState) -> float:
        """
        Structural stress compression: drawdown + slow recovery + tails.
        """
        draw = max(s.drawdown, 0.0)
        slow_heal = 1.0 / max(s.recovery_speed, 1e-3)
        tails = max(s.tail_risk_index, 0.0)

        stress_level = (
            draw +
            (slow_heal ** 0.5) +
            0.3 * tails
        )

        factor = 1.0 / (1.0 + self.config.stress_sensitivity * stress_level)
        return span * factor

    def _apply_covenant_penalty(self, span: float, violations: int) -> float:
        """
        Each violation shrinks span multiplicatively.
        """
        if violations <= 0:
            return self._clip_span(span)

        penalty_factor = 0.5 ** violations  # 1 violation halves span, etc.
        return self._clip_span(span * penalty_factor)

    def _clip_span(self, span: float) -> float:
        return max(self.config.min_span, min(self.config.max_span, span))

    def _trade_intensity_from_span(self, span: float, band: int) -> float:
        """
        Trade intensity co-moves with span, but
        is capped more aggressively in stressed bands.
        """
        # normalize span into [0,1] within [min_span, max_span]
        normalized = (
            (span - self.config.min_span)
            / max(self.config.max_span - self.config.min_span, 1e-6)
        )
        raw = normalized

        if band >= 2:
            raw *= 0.5  # extra damping in fragile / critical regimes

        return max(
            self.config.min_trade_intensity,
            min(self.config.max_trade_intensity, raw),
        )

    def _directional_bias_limit(self, band: int, violations: int) -> float:
        """
        How much net directional bias Alpha is allowed to hold.
        """
        if band == 0 and violations == 0:
            return 0.9
        if band == 1 and violations == 0:
            return 0.6
        if band == 2 and violations == 0:
            return 0.35

        # any violation or critical band => much lower bias
        return 0.15
