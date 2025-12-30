from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


# =========================
# Core Types & Enums
# =========================

class RegimeLabel(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    CRISIS = "crisis"
    RANGE = "range"
    SPIRAL = "spiral"
    UNKNOWN = "unknown"


class RegimeHardeningError(RuntimeError):
    """Raised when a parameter is so invalid that the engine must not run."""
    pass


# =========================
# Observation Layer
# =========================

@dataclass
class Observation:
    """
    One time-step snapshot from market + engine.

    NOTE:
    - asset_class 已经移除
    - 额外字段统一丢进 extra 就行
    """
    price: float
    ret_1d: float
    ret_14d: float
    volatility_20d: float  # e.g. realized vol or ATR / price
    volume: float
    volume_avg_20d: float

    # 会自动算，不传也可以
    volume_pressure: Optional[float] = None

    # 任意额外字段全部扔这里
    extra: Dict[str, Any] = field(default_factory=dict)

    def with_computed_volume_pressure(
        self,
        hard_cap: float = 10.0,
        eps: float = 1e-9
    ) -> "Observation":
        """
        Compute / clamp volume_pressure.

        volume_pressure ≈ current_volume / avg_volume_20d，
        然后加硬上限 hard_cap，避免参数离谱把引擎直接打爆。
        """
        if self.volume_avg_20d <= 0:
            vp = 0.0
        else:
            raw = self.volume / (self.volume_avg_20d + eps)
            vp = max(0.0, min(raw, hard_cap))  # clamp to [0, hard_cap]

        # “把 volume pressure 加到最大值”的含义：
        # - 如果 raw > hard_cap，就直接打到 hard_cap，而不是无限放大
        return Observation(
            price=self.price,
            ret_1d=self.ret_1d,
            ret_14d=self.ret_14d,
            volatility_20d=self.volatility_20d,
            volume=self.volume,
            volume_avg_20d=self.volume_avg_20d,
            volume_pressure=vp,
            extra=dict(self.extra),
        )


# =========================
# Risk Guards & Crash Line
# =========================

@dataclass
class RiskGuardConfig:
    """
    Global risk fences for all personas.
    """
    max_leverage: float = 5.0
    max_position_notional: float = 1.0  # normalized (e.g. fraction of NAV)
    max_step_change: float = 0.25       # max |Δexposure| per step

    # market-condition limits
    max_volume_pressure: float = 10.0
    max_volatility: float = 0.20        # 20% daily vol hard red-flag

    # drawdown lines
    warn_drawdown: float = 0.15         # soft brake
    panic_drawdown: float = 0.25        # heavy brake
    kill_drawdown: float = 0.35         # crash line: flatten everything

    # 如果有“参数过大直接不允许引擎运行”的阈值
    absolute_param_ceiling: float = 1e6


@dataclass
class RiskGuardState:
    """
    Things the guard needs from the engine.
    """
    equity_dd: float = 0.0  # 当前回撤，比如 0.20 = -20%
    extra: Dict[str, Any] = field(default_factory=dict)


class RiskGuard:
    """
    Risk-aware guard + crash-prevention line.
    """

    def __init__(self, cfg: RiskGuardConfig):
        self.cfg = cfg

    # ----- low-level hardening utilities -----

    def _ensure_finite_and_bounded(
        self,
        name: str,
        value: float,
        min_value: float = float("-inf"),
        max_value: float = float("inf"),
        hard: bool = False,
    ) -> float:
        """
        - If value is NaN/inf or outside [min_value, max_value]:
          - if hard=True -> raise RegimeHardeningError
          - else -> clamp
        """
        if value != value:  # NaN check
            if hard:
                raise RegimeHardeningError(f"{name} is NaN")
            return max(min_value, min(0.0, max_value))

        if value < min_value or value > max_value:
            if hard:
                raise RegimeHardeningError(
                    f"{name}={value} out of [{min_value}, {max_value}]"
                )
            return max(min_value, min(value, max_value))

        return value

    def fullness_overflow(
        self,
        pressure: float,
        soft_level: float = 1.0,
        full_level: float = 3.0,
        min_factor: float = 0.4,
    ) -> float:
        """
        满溢方程：给 volume_pressure / 任意“压力”一个 [0,1] 的缩放因子。

        - pressure <= soft_level:       factor = 1.0   （正常水位）
        - soft_level < pressure < full_level:
              用平滑曲线从 1.0 下降到 min_factor
        - pressure >= full_level:       factor = min_factor （已经“溢出”，强力压缩）

        数学上用的是一个简单的二次缓降:
            t = ((pressure - soft) / (full - soft)) ∈ [0,1]
            factor = 1 - (1 - min_factor) * t^2
        """
        if pressure <= soft_level:
            return 1.0

        full_level = max(full_level, soft_level + 1e-6)

        t = (pressure - soft_level) / (full_level - soft_level)
        t = max(0.0, min(t, 1.0))

        factor = 1.0 - (1.0 - min_factor) * (t * t)
        return max(min_factor, min(factor, 1.0))

    def harden_observation(self, obs: Observation) -> Observation:
        """
        Make sure observation is within sane bounds.
        If something is completely insane -> raise.
        """
        # price & volumes
        if obs.price <= 0:
            raise RegimeHardeningError(f"Non-positive price: {obs.price}")
        if obs.volume < 0 or obs.volume_avg_20d < 0:
            raise RegimeHardeningError("Negative volume is not allowed")

        # volatility sanity
        self._ensure_finite_and_bounded(
            "volatility_20d",
            obs.volatility_20d,
            0.0,
            self.cfg.absolute_param_ceiling,
            hard=True,
        )

        # compute & clamp volume pressure
        obs_hardened = obs.with_computed_volume_pressure(
            hard_cap=self.cfg.max_volume_pressure
        )

        # volume_pressure 也做一次 hard 检查
        if obs_hardened.volume_pressure is not None:
            self._ensure_finite_and_bounded(
                "volume_pressure",
                obs_hardened.volume_pressure,
                0.0,
                self.cfg.max_volume_pressure,
                hard=True,
            )

        return obs_hardened

    # ----- crash-prevention line -----

    def crash_prevention_scale(
        self,
        guard_state: RiskGuardState,
        obs: Observation,
    ) -> float:
        """
        Returns a multiplicative scale in [0, 1].

        1. 基于 drawdown 画一条分段线
        2. 基于 volatility / volume pressure 做额外压缩
        """
        dd = guard_state.equity_dd

        # drawdown-based line
        if dd >= self.cfg.kill_drawdown:
            base_scale = 0.0  # full flatten
        elif dd >= self.cfg.panic_drawdown:
            # 从 panic_drawdown 到 kill_drawdown，线性从 0.2 -> 0
            span = self.cfg.kill_drawdown - self.cfg.panic_drawdown
            span = max(span, 1e-9)
            frac = (self.cfg.kill_drawdown - dd) / span
            base_scale = 0.2 * frac
        elif dd >= self.cfg.warn_drawdown:
            # 从 warn_drawdown 到 panic_drawdown，线性从 0.6 -> 0.2
            span = self.cfg.panic_drawdown - self.cfg.warn_drawdown
            span = max(span, 1e-9)
            frac = (self.cfg.panic_drawdown - dd) / span
            base_scale = 0.2 + 0.4 * frac
        else:
            base_scale = 1.0

        # volatility pressure
        vol_penalty = 1.0
        if obs.volatility_20d > self.cfg.max_volatility:
            ratio = obs.volatility_20d / self.cfg.max_volatility
            vol_penalty = max(0.3, 1.0 / ratio)

        # volume pressure 使用满溢方程
        vp_penalty = 1.0
        if obs.volume_pressure is not None:
            vp_penalty = self.fullness_overflow(
                pressure=obs.volume_pressure,
                soft_level=1.0,
                full_level=3.0,
                min_factor=0.4,
            )

        scale = base_scale * vol_penalty * vp_penalty
        return max(0.0, min(scale, 1.0))

    # ----- step-law for exposure -----

    def apply_step_law(
        self,
        prev_exposure: float,
        raw_target: float,
    ) -> float:
        """
        Law of moving steps:
        限制每一步 max_step_change，并且保证暴露在
        [-max_position_notional, max_position_notional] 之内
        """
        prev_exposure = self._ensure_finite_and_bounded(
            "prev_exposure",
            prev_exposure,
            -self.cfg.max_position_notional,
            self.cfg.max_position_notional,
            hard=False,
        )
        raw_target = self._ensure_finite_and_bounded(
            "raw_target",
            raw_target,
            -self.cfg.max_position_notional,
            self.cfg.max_position_notional,
            hard=False,
        )

        delta = raw_target - prev_exposure
        max_step = self.cfg.max_step_change

        if abs(delta) <= max_step:
            new_exp = raw_target
        else:
            new_exp = prev_exposure + max_step * (1 if delta > 0 else -1)

        return self._ensure_finite_and_bounded(
            "new_exposure",
            new_exp,
            -self.cfg.max_position_notional,
            self.cfg.max_position_notional,
            hard=False,
        )


# =========================
# Regime Personas
# =========================

@dataclass
class PersonaState:
    prev_exposure: float = 0.0
    prev_regime: RegimeLabel = RegimeLabel.UNKNOWN
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaDecision:
    target_exposure: float
    regime: RegimeLabel
    notes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class RegimePersona:
    """
    Base persona. Concrete personas implement `raw_signal`.
    """

    name: str = "base"

    def raw_signal(self, obs: Observation) -> float:
        """
        Returns an unconstrained desired exposure in [-1, 1].
        子类实现具体策略逻辑。
        """
        raise NotImplementedError

    def classify_regime(self, obs: Observation) -> RegimeLabel:
        """
        简单 regime 规则（螺旋周期版）：

        - CRISIS:
            - 波动极高 或
            - 短期/中期收益极端下杀
        - BULL / BEAR:
            - 有方向性趋势，14日 + 1日 同号且绝对值不太小
        - RANGE（箱体横盘）:
            - 14日和1日都在极小区间内震荡，波动也偏低
            - 像贴着一条小直线爬
        - SPIRAL（螺旋周期）:
            - 总体没有大趋势（14日净变化不大）
            - 但波动中等，来回绕着“均值”打圈
        - UNKNOWN:
            - 兜底情况
        """
        # 1) CRISIS 先拦截
        if (
            obs.volatility_20d > 0.30
            or obs.ret_1d <= -0.06
            or obs.ret_14d <= -0.12
        ):
            return RegimeLabel.CRISIS

        # 2) 趋势性：BULL / BEAR
        if obs.ret_14d > 0.03 and obs.ret_1d > 0.005:
            return RegimeLabel.BULL
        if obs.ret_14d < -0.03 and obs.ret_1d < -0.005:
            return RegimeLabel.BEAR

        # 3) RANGE：小幅震荡 + 低波动（几乎水平线）
        if (
            -0.01 <= obs.ret_14d <= 0.01
            and -0.003 <= obs.ret_1d <= 0.003
            and obs.volatility_20d < 0.15
        ):
            return RegimeLabel.RANGE

        # 4) SPIRAL（螺旋周期）：
        #    没有明显趋势，但波动不算低，价格绕均值上下摆动
        if (
            abs(obs.ret_14d) <= 0.02     # 净方向不强
            and 0.15 <= obs.volatility_20d < 0.28
        ):
            return RegimeLabel.SPIRAL

        # 5) 兜底
        return RegimeLabel.UNKNOWN

    def decide(
        self,
        obs: Observation,
        guard: RiskGuard,
        guard_state: RiskGuardState,
        persona_state: PersonaState,
    ) -> PersonaDecision:
        """
        - harden obs
        - get raw signal in [-1, 1]
        - apply crash-prevention + step-law
        """
        obs_h = guard.harden_observation(obs)
        regime = self.classify_regime(obs_h)

        raw = self.raw_signal(obs_h)
        raw = max(-1.0, min(raw, 1.0))

        # crash prevention
        crash_scale = guard.crash_prevention_scale(guard_state, obs_h)
        safe_raw = raw * crash_scale

        # law of moving steps
        stepped = guard.apply_step_law(
            prev_exposure=persona_state.prev_exposure,
            raw_target=safe_raw,
        )

        notes = (
            f"persona={self.name}, regime={regime.value}, "
            f"raw={raw:.3f}, crash_scale={crash_scale:.3f}, "
            f"stepped={stepped:.3f}"
        )

        return PersonaDecision(
            target_exposure=stepped,
            regime=regime,
            notes=notes,
            extra={
                "raw_signal": raw,
                "crash_scale": crash_scale,
                "volume_pressure": obs_h.volume_pressure,
            },
        )


# ----- Example concrete personas -----

class TrendFollowerPersona(RegimePersona):
    name = "trend_follower"

    def raw_signal(self, obs: Observation) -> float:
        # 简单趋势逻辑：14日 > 0 & 1日 > 0 -> 做多；反之做空；否则中性
        strength = 0.0

        if obs.ret_14d > 0 and obs.ret_1d > 0:
            strength = min(1.0, obs.ret_14d / 0.05)
        elif obs.ret_14d < 0 and obs.ret_1d < 0:
            strength = -min(1.0, abs(obs.ret_14d) / 0.05)
        else:
            strength = 0.0

        # 危险时段：高 vol + 高 volume pressure -> 降杠杆
        if obs.volatility_20d > 0.25 or (obs.volume_pressure or 0) > 3.0:
            strength *= 0.5

        return max(-1.0, min(strength, 1.0))


class MeanReversionPersona(RegimePersona):
    name = "mean_reversion"

    def raw_signal(self, obs: Observation) -> float:
        # 简单均值回复：短期跌多了想反弹，涨多了想回落
        strength = 0.0
        if obs.ret_1d < -0.02:
            strength = 0.7  # buy dip
        elif obs.ret_1d > 0.02:
            strength = -0.7  # fade rip

        # 高波动、高量压时，强度自动减半
        if obs.volatility_20d > 0.20 or (obs.volume_pressure or 0) > 2.0:
            strength *= 0.5

        return max(-1.0, min(strength, 1.0))


class CrisisDefenderPersona(RegimePersona):
    """
    专门在 CRISIS / 高 drawdown 时被 Router 召唤：
    - 优先保护下行，尽量往 0 或轻微对冲靠。
    """
    name = "crisis_defender"

    def raw_signal(self, obs: Observation) -> float:
        # 默认收风险：靠近 0 或轻微对冲
        strength = -0.2  # 轻微做空对冲

        # 如果短期暴跌已经发生，进一步减仓或反弹保护
        if obs.ret_1d < -0.05 or obs.ret_14d < -0.1:
            strength = -0.4

        # 如果已经放量恐慌，进一步收杠杆
        if (obs.volume_pressure or 0) > 3.0:
            strength *= 0.5

        return max(-1.0, min(strength, 1.0))


# =========================
# Simple Regime Engine
# =========================

@dataclass
class RegimeEngineState:
    persona_state: PersonaState = field(default_factory=PersonaState)
    guard_state: RiskGuardState = field(default_factory=RiskGuardState)
    extra: Dict[str, Any] = field(default_factory=dict)

class RoyalLegalPersona(RegimePersona):
    """
    ROYAL LEGAL persona:
    - 负责解读 legal / compliance 风险信号
    - 在高法律风险、制裁风险、司法辖区封锁时强力收敛仓位
    - 在风险可控时，允许顺着 regime 做温和方向暴露

    预期从 obs.extra 里读取的字段（如果没有就默认安全）：
      - legal_risk_score: float in [0, 1] （综合合规/监管风险）
      - litigation_risk_score: float in [0, 1] （诉讼/索赔风险）
      - sanction_flag: bool （是否涉及制裁名单/受限实体）
      - jurisdiction_blocked: bool （司法辖区禁止或强监管）
    """
    name = "royal_legal"

    def raw_signal(self, obs: Observation) -> float:
        extra = obs.extra or {}

        # ---- 解析法律风险因子 ----
        legal_risk = float(extra.get("legal_risk_score", 0.0) or 0.0)
        litigation_risk = float(extra.get("litigation_risk_score", 0.0) or 0.0)
        sanction_flag = bool(extra.get("sanction_flag", False))
        jurisdiction_blocked = bool(extra.get("jurisdiction_blocked", False))

        # clamp 到 [0, 1]
        legal_risk = max(0.0, min(legal_risk, 1.0))
        litigation_risk = max(0.0, min(litigation_risk, 1.0))

        combined_risk = max(legal_risk, litigation_risk)

        # ---- regime 方向：只给一个温和的“基准方向” ----
        regime = self.classify_regime(obs)

        if regime == RegimeLabel.BULL:
            base = 0.5      # 合规通过时最多中等偏多
        elif regime in (RegimeLabel.BEAR, RegimeLabel.CRISIS):
            base = -0.5     # 在下行/危机里更偏防守
        elif regime == RegimeLabel.SPIRAL:
            base = 0.2      # 螺旋周期：轻微顺势
        elif regime == RegimeLabel.RANGE:
            base = 0.0      # 区间震荡：法务 persona 不主动押方向
        else:
            base = 0.0

        # ---- 硬约束：制裁/封锁 -> 强制 0 曝露（让 step_law 慢慢回 0）----
        if sanction_flag or jurisdiction_blocked:
            return 0.0

        # ---- 软约束：法律风险分段压缩基准仓位 ----
        # combined_risk ∈ [0,1]
        if combined_risk >= 0.8:
            # 极高法律风险：几乎不许动，直接归零
            return 0.0
        elif combined_risk >= 0.5:
            # 高风险：只保留 30% 基准暴露
            return base * 0.3
        elif combined_risk >= 0.2:
            # 中等风险：保留 60% 基准暴露
            return base * 0.6
        else:
            # 低风险：完全允许基准暴露
            return base



class RegimeEngine:
    """
    Glue between FDE core and persona layer.

    asset_class 已经移除；外部如果需要就放到 extra 里传进来。
    """

    def __init__(
        self,
        personas: Dict[str, RegimePersona],
        guard_cfg: Optional[RiskGuardConfig] = None,
    ):
        self.personas = personas
        self.guard = RiskGuard(guard_cfg or RiskGuardConfig())

    def step(
        self,
        persona_key: str,
        obs: Observation,
        engine_state: RegimeEngineState,
    ) -> PersonaDecision:
        if persona_key not in self.personas:
            raise KeyError(f"Unknown persona: {persona_key}")

        persona = self.personas[persona_key]

        decision = persona.decide(
            obs=obs,
            guard=self.guard,
            guard_state=engine_state.guard_state,
            persona_state=engine_state.persona_state,
        )

        # 更新内部状态
        engine_state.persona_state.prev_exposure = decision.target_exposure
        engine_state.persona_state.prev_regime = decision.regime

        return decision


# 默认 persona 集合，给 FDE 直接 import 使用
DEFAULT_PERSONAS: Dict[str, RegimePersona] = {
    "trend": TrendFollowerPersona(),
    "mean_rev": MeanReversionPersona(),
    "crisis": CrisisDefenderPersona(),
    "royal_legal":RoyalLegalPersona()
}
