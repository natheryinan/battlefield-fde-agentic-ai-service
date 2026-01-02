
class RegimeEngine:

    def __init__(
        self,
        vol_elasticity_baseline: float = 1.0,
        shock_escalation_strength: float = 2.0,
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
        """
        Volatility is elastic — trend reinforces magnitude.
        """
        realized = max(v.realized, 0.0)
        trend = max(v.trend, 0.0)

        base = realized * self.vol_elasticity_baseline
        reinforcement = trend ** 1.25

        if v.forecast is not None:
            # gently pull towards forecast
            base = 0.7 * base + 0.3 * v.forecast

        return base + reinforcement

    def _liquidity_fragility(self, l: LiquidityState):
        """
        Thin books + wide spreads + high impact cost -> fragility.
        Elasticity tempers the penalty.
        """
        depth_term = (1.0 / max(l.depth, 1e-6)) ** 0.6
        spread_term = l.spread
        impact_term = l.impact_cost ** 0.9
        elasticity_cushion = 1.0 / max(l.elasticity, 1e-3)

        raw = depth_term + spread_term + impact_term
        return self.liquidity_fragility_weight * raw * elasticity_cushion

    def _flow_tension(self, f: FlowState):
        """
        Flow tension from directional pressure + crowding.
        """
        pressure_term = abs(f.pressure) ** 1.1
        inflow_term = max(f.net_inflow_ratio, 0.0) ** 0.7
        crowding_term = f.crowding_index ** 1.2

        return self.flow_crowding_weight * (pressure_term + inflow_term + crowding_term)

    def _structural_shock(self, s: StressState):
        """
        Structural shocks from drawdown + slow recovery + tails.
        """
        drawdown_term = s.drawdown ** 1.2
        slow_heal_penalty = (1.0 / max(s.recovery_speed, 1e-3)) ** 0.5
        tail_term = self.tail_risk_weight * s.tail_risk_index ** 1.3

        structural = drawdown_term + slow_heal_penalty + tail_term
        return self.shock_escalation_strength * structural

    # ----- public interface --------------------------------------------

    def evaluate(self, m: MarketState) -> RegimeAssessment:
        vol_part = self._elastic_vol_intensity(m.volatility)
        liq_part = self._liquidity_fragility(m.liquidity)
        flow_part = self._flow_tension(m.flow)
        shock_part = self._structural_shock(m.stress)

        score = float(vol_part + liq_part + flow_part + shock_part)
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

    def _constraints_from_band(self, band: int):
        """
        Translate regime band into hard controls.
        This is where SovereignRouter can later override / refine.
        """
        if band == 0:
            return 3.0, 0.35, 0.50   # leverage, pos_change, gross_shift
        if band == 1:
            return 2.0, 0.25, 0.35
        if band == 2:
            return 1.2, 0.15, 0.20
        # band 3: critical
        return 0.5, 0.08, 0.10

    def _alpha_guidance(self, band: int) -> str:
        if band == 0:
            return "Run full playbook; favor carry and convexity harvesting."
        if band == 1:
            return "Prioritize resilient alphas; cap tail-heavy structures."
        if band == 2:
            return "Focus on defense-weighted alphas; shrink trade frequency."
        return "Suspend offensive alphas; allow only hedging or de-risk flows."

    def _guardian_guidance(self, band: int) -> str:
        if band == 0:
            return "Soft monitoring; record spans, no blade drawn."
        if band == 1:
            return "Tighten risk spans; pre-arm circuit breakers."
        if band == 2:
            return "Clamp spans; auto-override any leverage expansion."
        return "Force global cutdown; hold risk in quarantine mode."

    def _liquidity_guidance(self, band: int) -> str:
        if band == 0:
            return "Normal routing; cross venues for best price."
        if band == 1:
            return "Favor deeper venues; cap order slice size."
        if band == 2:
            return "Route only to deepest pools; stagger execution."
        return "Halt aggressive routing; permit exits only with micro-slices."
