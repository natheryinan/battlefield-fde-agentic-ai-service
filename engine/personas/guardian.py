from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import math


@dataclass
class Observation:
    """
    Single snapshot of market / environment state
    that Guardian will watch.

    Notes:
      - volatility is a signed shock (can be negative or positive).
      - liquidity_score is a continuous depth signal:
          * higher  → deeper / healthier liquidity
          * lower   → thinner / stressed
    """
    timestamp: datetime
    price: float

    # Volatility is a signed "shock" signal:
    # can alternate between negative and positive, with large magnitude
    # (and even ±inf) indicating extreme instability.
    volatility: float

    volume: float              # raw or normalized
    volume_pressure: float     # pressure indicator (e.g. VPIN or custom score)
    drawdown: float            # realized DD in 0-1 (0.2 = -20%)

    # Liquidity depth score. You decide scaling:
    # - 1.0   ≈ "comfortable" depth
    # - < 1.0 ≈ thinner
    # - 0.0   ≈ fully frozen
    liquidity_score: float

    extra: Dict[str, Any]      # anything else you want to pass through


@dataclass
class GuardianThresholds:
    """
    Volatility + liquidity as oscillating / collapsing fields.

    Volatility:
      - |volatility| below baseline → normal noise
      - grows with shock_scale      → stress accumulates

    Liquidity:
      - >= liquidity_baseline       → comfortable
      - between freeze_level and baseline → thinning / stress
      - <= liquidity_freeze_level   → frozen, near-CRASH by itself
    """

    # ---- volatility shock parameters ----
    max_volatility_baseline: float = 0.02     # normal oscillation tolerance
    volatility_shock_scale: float = 0.08      # how aggressively severity ramps as |vol| grows

    # ---- drawdown / volume thresholds ----
    max_drawdown: float = 0.15
    max_volume_pressure: float = 3.0

    # ---- liquidity shock parameters ----
    liquidity_baseline: float = 0.60          # comfy depth; above this → no stress
    liquidity_shock_scale: float = 0.40       # how strongly stress rises as depth thins
    liquidity_freeze_level: float = 0.15      # below this → market considered "frozen"

    # ---- hard crash bands ----
    crash_drawdown: float = 0.30
    crash_volatility: float = 0.15            # |vol| at/above this → CRASH zone


@dataclass
class GuardianAssessment:
    """
    Guardian's view of the current state.
    """
    regime: str                     # "NORMAL", "STRESSED", "CRASH"
    breach: bool                    # True if any metric beyond its safe band
    severity: float                 # 0-1 aggregate severity
    reasons: Dict[str, float]       # metric_name -> normalized breach level
    timestamp: datetime


class Guardian:
    """
    Risk guardian that watches Observation streams.

    - Does NOT know about Alpha's covenant window.
    - Purely local risk classifier.
    - Output feeds into the regime/router layer which *is*
      wrapped by Alpha's covenant.

    Volatility behavior:
      - We use |volatility| for breach checks.
      - Non-finite values (NaN / ±inf) are treated as "infinite" breach.

    Liquidity behavior:
      - Deep (>= baseline) → no liquidity stress.
      - Thinning (< baseline) → stress grows with liquidity_shock_scale.
      - Frozen (<= freeze_level) → forces CRASH regime and spikes severity.
    """

    def __init__(self, thresholds: Optional[GuardianThresholds] = None):
        self.thresholds = thresholds or GuardianThresholds()

    def _finite_or_max(self, value: float, max_scale: float = 10.0) -> float:
        """
        Map non-finite volatility values to a very large finite magnitude
        so that severity saturates near 1.0.
        """
        if not math.isfinite(value):
            return max_scale
        return value

    def assess(self, obs: Observation) -> GuardianAssessment:
        t = self.thresholds
        reasons: Dict[str, float] = {}

        # ---------- volatility shock ----------
        vol_mag = abs(self._finite_or_max(obs.volatility))
        safe_band = t.max_volatility_baseline
        shock_band = max(t.volatility_shock_scale, 1e-9)  # avoid division by zero

        # vol_mag <= safe_band → 0
        # vol_mag = safe_band + shock_band → 1
        vol_ratio = max(0.0, (vol_mag - safe_band) / shock_band)

        # ---------- drawdown ----------
        dd_ratio = max(0.0, obs.drawdown / t.max_drawdown - 1.0)

        # ---------- liquidity shock ----------
        liq_safe = t.liquidity_baseline
        liq_shock = max(t.liquidity_shock_scale, 1e-9)

        if obs.liquidity_score >= liq_safe:
            liq_ratio = 0.0
        else:
            liq_ratio = (liq_safe - obs.liquidity_score) / liq_shock

        # Extra: hard illiquidity "freeze" flag
        liquidity_frozen = obs.liquidity_score <= t.liquidity_freeze_level

        # ---------- volume pressure ----------
        vp_ratio = max(0.0, obs.volume_pressure / t.max_volume_pressure - 1.0)

        # ---------- record reasons ----------
        if vol_ratio > 0:
            reasons["volatility_shock"] = vol_ratio
        if dd_ratio > 0:
            reasons["drawdown"] = dd_ratio
        if liq_ratio > 0:
            reasons["liquidity_thinning"] = liq_ratio
        if liquidity_frozen:
            # big constant to strongly pull severity toward 1
            reasons["liquidity_freeze"] = reasons.get("liquidity_freeze", 0.0) + 3.0
        if vp_ratio > 0:
            reasons["volume_pressure"] = vp_ratio

        # ---------- aggregate severity ----------
        raw_score = sum(reasons.values())
        if raw_score <= 0:
            severity = 0.0
        else:
            # 1 - exp(-x): as raw_score → ∞, severity → 1
            severity = 1.0 - math.exp(-raw_score)

        # ---------- regime classification ----------
        if severity == 0.0:
            regime = "NORMAL"
        else:
            # liquidity freeze OR hardcore vol/dd can force CRASH
            if (
                liquidity_frozen
                or obs.drawdown >= t.crash_drawdown
                or vol_mag >= t.crash_volatility
            ):
                regime = "CRASH"
                # ensure very high severity in true freeze/collapse
                severity = max(severity, 0.95)
            else:
                regime = "STRESSED"

        return GuardianAssessment(
            regime=regime,
            breach=severity > 0.0,
            severity=severity,
            reasons=reasons,
            timestamp=obs.timestamp,
        )
