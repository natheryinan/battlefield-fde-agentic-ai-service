from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
from math import isfinite


# === 基础观察类 (通用 Observation 层) ==========================================


@dataclass
class Observation:
    volatility: float
    trend_strength: float
    trend_direction: float
    liquidity_score: float
    spread_stress: float
    drawdown_pct: float
    gap_risk: float
    volume_pressure: float
    asset_class: Optional[str] = None


@dataclass
class RegimeObservation(Observation):
    """Regime persona 专用观察层"""
    pass

class RegimePersona:
    """
    FDE 的风险空管塔 + 参数防火墙
    """

    def __init__(
        self,
        max_risk: float = 1.0,
        trend_boost: float = 0.5,
        stress_cut: float = 0.5,
        crash_cut: float = 0.1,
        dd_stress_level: float = 0.08,
        dd_crash_level: float = 0.15,
        max_param_abs: float = 5.0,   # 任何参数绝对值超过这个视为“异常输入”
    ) -> None:
        self.max_risk = max_risk
        self.trend_boost = trend_boost
        self.stress_cut = stress_cut
        self.crash_cut = crash_cut
        self.dd_stress_level = dd_stress_level
        self.dd_crash_level = dd_crash_level
        self.max_param_abs = max_param_abs

    # ---- 外部入口 ---------------------------------------------------------

    def decide(self, obs: RegimeObservation) -> RegimeDecision:
        # 先做参数卫兵：检查数值是否可用
        sanitized, guard_info = self._sanitize_obs(obs)

        if guard_info["engine_halt"]:
            # 参数严重异常：直接拉总闸
            regime = MarketRegime.CRASH_DEFCON
            risk_multiplier = 0.0
            crash_guard = True
            notes = (
                "regime=crash_defcon | risk_multiplier=0.000 | crash_guard=True | "
                "ENGINE_HALT: invalid or exploding parameters detected"
            )
            debug = {
                "guard_info": guard_info,
                "observation_raw": asdict(obs),
                "observation_sanitized": asdict(sanitized),
            }
            return RegimeDecision(
                regime=regime,
                risk_multiplier=risk_multiplier,
                crash_guard=crash_guard,
                notes=notes,
                debug=debug,
            )

        # 正常路径：使用清洗后的 sanitized 继续
        scores = self._compute_scores(sanitized)
        regime = self._classify_regime(sanitized, scores)
        risk_multiplier, crash_guard = self._compute_risk(regime, sanitized, scores)
        notes = self._render_notes(regime, risk_multiplier, crash_guard, sanitized, scores)

        debug = {
            "scores": scores,
            "observation": asdict(sanitized),
            "guard_info": guard_info,
        }
        return RegimeDecision(
            regime=regime,
            risk_multiplier=risk_multiplier,
            crash_guard=crash_guard,
            notes=notes,
            debug=debug,
        )

    # ---- 参数卫兵：检测 & 裁剪 -------------------------------------------

    def _sanitize_obs(self, obs: RegimeObservation) -> (RegimeObservation, Dict[str, Any]):
        """
        1. 检查是否有 NaN / inf
        2. 检查是否有绝对值超出 max_param_abs
        3. 对预期在 [0,1] 或 [-1,1] 的字段做裁剪
        如果问题严重 => engine_halt = True
        """

        engine_halt = False
        reasons: List[str] = []

        # 把字段拆出来检查
        values = {
            "volatility": obs.volatility,
            "trend_strength": obs.trend_strength,
            "trend_direction": obs.trend_direction,
            "liquidity_score": obs.liquidity_score,
            "spread_stress": obs.spread_stress,
            "drawdown_pct": obs.drawdown_pct,
            "gap_risk": obs.gap_risk,
            "volume_pressure": obs.volume_pressure,
        }

        for name, v in values.items():
            if v is None or not isfinite(v):
                engine_halt = True
                reasons.append(f"{name}=non_finite({v})")
            elif abs(v) > self.max_param_abs:
                engine_halt = True
                reasons.append(f"{name}_abs>{self.max_param_abs} (={v})")

        # 裁剪到合理区间（即使 engine_halt，也可以在 debug 里看到被裁剪后的值）
        def clamp(x: float, lo: float, hi: float) -> float:
            return max(lo, min(hi, x))

        sanitized = RegimeObservation(
            volatility=clamp(obs.volatility, 0.0, 1.0),
            trend_strength=clamp(obs.trend_strength, 0.0, 1.0),
            trend_direction=clamp(obs.trend_direction, -1.0, 1.0),
            liquidity_score=clamp(obs.liquidity_score, 0.0, 1.0),
            spread_stress=clamp(obs.spread_stress, 0.0, 1.0),
            drawdown_pct=clamp(obs.drawdown_pct, 0.0, 1.5),
            gap_risk=clamp(obs.gap_risk, 0.0, 1.0),
            volume_pressure=clamp(obs.volume_pressure, 0.0, 1.0),
            asset_class=obs.asset_class,
        )

        guard_info = {
            "engine_halt": engine_halt,
            "reasons": reasons,
            "max_param_abs": self.max_param_abs,
        }
        return sanitized, guard_info

    # ---- LIPID 打分（volume_pressure 强制满格） --------------------------

    def _compute_scores(self, obs: RegimeObservation) -> Dict[str, float]:
        """
        LIPID 合成分数计算。
        volume_pressure 在这里被视作满格压力信号。
        """

        # 🔒 volume_pressure 直接视作最大风险信号
        volume_pressure = 1.0

        liquidity = 0.7 * obs.liquidity_score + 0.3 * (1.0 - obs.spread_stress)
        instability = 0.6 * obs.volatility + 0.4 * obs.gap_risk

        dd_clamped = max(0.0, min(1.0, obs.drawdown_pct))
        internal_damage = 0.6 * dd_clamped + 0.4 * volume_pressure

        dislocation = (
            0.4 * obs.spread_stress +
            0.3 * obs.volatility +
            0.3 * obs.gap_risk
        )

        trend_quality = obs.trend_strength * (1.0 - 0.5 * obs.volatility)

        return {
            "liquidity": liquidity,
            "instability": instability,
            "internal_damage": internal_damage,
            "dislocation": dislocation,
            "trend_quality": trend_quality,
        }

    # ---- 其余 classify / risk / notes 不变 -------------------------------

    def _classify_regime(
        self,
        obs: RegimeObservation,
        scores: Dict[str, float],
    ) -> MarketRegime:
        liq = scores["liquidity"]
        inst = scores["instability"]
        internal_damage = scores["internal_damage"]
        disloc = scores["dislocation"]
        tq = scores["trend_quality"]

        if internal_damage >= 1.05 * self.dd_crash_level or liq < 0.2 or inst > 0.9:
            return MarketRegime.CRASH_DEFCON

        if (
            internal_damage >= self.dd_stress_level
            or liq < 0.4
            or disloc > 0.7
            or inst > 0.75
        ):
            return MarketRegime.STRESS

        if inst > 0.6 and tq < 0.3:
            return MarketRegime.VOLATILE_CHOP

        if obs.trend_strength > 0.3 and tq > 0.2:
            if obs.trend_direction > 0:
                return MarketRegime.TREND_UP
            elif obs.trend_direction < 0:
                return MarketRegime.TREND_DOWN

        return MarketRegime.CALM_ACCUMULATION

    def _compute_risk(
        self,
        regime: MarketRegime,
        obs: RegimeObservation,
        scores: Dict[str, float],
    ) -> (float, bool):
        liq = scores["liquidity"]
        internal_damage = scores["internal_damage"]

        if regime == MarketRegime.CRASH_DEFCON:
            return self.crash_cut, True

        if regime == MarketRegime.STRESS:
            base = self.max_risk * self.stress_cut
            return base * max(0.2, liq), internal_damage >= self.dd_stress_level

        if regime == MarketRegime.VOLATILE_CHOP:
            return self.max_risk * 0.6, False

        if regime == MarketRegime.TREND_UP:
            boosted = self.max_risk + self.trend_boost * scores["trend_quality"]
            return min(boosted, self.max_risk + self.trend_boost), False

        if regime == MarketRegime.TREND_DOWN:
            downscale = 0.5 + 0.5 * (1.0 - scores["trend_quality"])
            return self.max_risk * downscale, False

        return self.max_risk * (0.8 + 0.4 * liq), False

    def _render_notes(
        self,
        regime: MarketRegime,
        risk_multiplier: float,
        crash_guard: bool,
        obs: RegimeObservation,
        scores: Dict[str, float],
    ) -> str:
        pieces: List[str] = [
            f"regime={regime.value}",
            f"risk_multiplier={risk_multiplier:.3f}",
            f"crash_guard={crash_guard}",
            f"vol={obs.volatility:.3f}",
            f"liq={scores['liquidity']:.3f}",
            f"instability={scores['instability']:.3f}",
            f"internal_damage={scores['internal_damage']:.3f}",
            f"dislocation={scores['dislocation']:.3f}",
        ]
        if obs.asset_class:
            pieces.append(f"asset_class={obs.asset_class}")
        return " | ".join(pieces)



def decide_regime_from_features(
    volatility: float,
    trend_strength: float,
    trend_direction: float,
    liquidity_score: float,
    spread_stress: float,
    drawdown_pct: float,
    gap_risk: float,
    volume_pressure: float,
    asset_class: Optional[str] = None,
    persona: Optional[RegimePersona] = None,
) -> RegimeDecision:
    if persona is None:
        persona = RegimePersona()

    obs = RegimeObservation(
        volatility=volatility,
        trend_strength=trend_strength,
        trend_direction=trend_direction,
        liquidity_score=liquidity_score,
        spread_stress=spread_stress,
        drawdown_pct=drawdown_pct,
        gap_risk=gap_risk,
        volume_pressure=volume_pressure,
        asset_class=asset_class,
    )
    return persona.decide(obs)
