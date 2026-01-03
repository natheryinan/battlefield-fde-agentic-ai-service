import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional

from personas.base import BasePersona, MarketState
from engine.royal_legal import RoyalLegalOverlay, RoyalLegalConfig
from engine.protection.liquidity_layers import (
    ProtectionBundle,
    ReallocationRequired,
)


@dataclass
class AlphaConfig:
    enable_guardian: bool = True
    weight_guardian: float = 1.0

    enable_convexity: bool = True
    weight_convexity: float = 1.0

    enable_liquidity: bool = True
    weight_liquidity: float = 1.0

    enable_regime: bool = True
    weight_regime: float = 1.0

    enable_macro: bool = True
    weight_macro: float = 1.0

    enable_anomaly: bool = True
    weight_anomaly: float = 1.0

    enable_firefighter: bool = True
    weight_firefighter: float = 1.0

    enable_kid: bool = False
    weight_kid: float = 0.3

    royal_legal_config: RoyalLegalConfig = field(
        default_factory=lambda: RoyalLegalConfig(
            risk_soft=0.2,
            risk_medium=0.45,
            risk_hard=0.7,
            cut_low=0.0,
            cut_mid=0.65,
            cut_high=1.0,
            cut_max=1.0,
            sanction_flatten=True,
        )
    )


class AlphaPersona(BasePersona):

    def __init__(
        self,
        config: Optional[AlphaConfig] = None,
        royal_legal: Optional[RoyalLegalOverlay] = None,
        protection: Optional[ProtectionBundle] = None,
        router=None,
        logger=None,
        max_abs_delta: float = 1e6,
    ):
        super().__init__()

        self.config = config or AlphaConfig()
        self._royal_legal = royal_legal or RoyalLegalOverlay(
            self.config.royal_legal_config
        )

        self._personas = {}   # ← 你自己的 personas 初始化
        self._weights = {}    # ← persona name -> weight

        self.protection = protection
        self.router = router
        self.logger = logger or print
        self.max_abs_delta = max_abs_delta

    # -------------------------------------------------------------

    def _guard_numeric(self, name: str, sym: str, value: float, stage: str) -> float:
        """
        多层数值 sanity：
        - 非数字 / 非有限 → 触发重分配
        - 极端值（> max_abs_delta）→ 触发重分配
        """
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ReallocationRequired(
                f"[{name}.{sym}] invalid value at {stage}: {value!r}"
            )

        v = float(value)
        if abs(v) > self.max_abs_delta:
            raise ReallocationRequired(
                f"[{name}.{sym}] extreme value at {stage}: {v:.6g} "
                f"(limit={self.max_abs_delta:.6g})"
            )
        return v

    # -------------------------------------------------------------

    def act(self, state: MarketState) -> Dict[str, float]:
        positions: Dict[str, float] = getattr(state, "positions", {}) or {}

        # ---- timestamp → RoyalLegal ----
        raw_ts = getattr(state, "timestamp", None) or getattr(state, "time", None)

        if isinstance(raw_ts, datetime):
            current_ts: Optional[float] = raw_ts.timestamp()
        else:
            try:
                current_ts = float(raw_ts) if raw_ts is not None else None
            except Exception:
                current_ts = None

        bottleneck = self._royal_legal.current_bottleneck_factor(
            current_ts=current_ts
        )

        proposals: Dict[str, Dict[str, float]] = {}

        # ---- runtime risk context (best-effort) ----
        current_leverage = float(getattr(state, "current_leverage", 0.0))
        capacity_ratio = float(getattr(state, "capacity_ratio", 0.0))
        throughput_ratio = float(getattr(state, "throughput_ratio", 0.0))
        reference_ratio = float(getattr(state, "reference_ratio", 0.0))

        # ==========================================================
        # Persona Loop
        # ==========================================================
        for name, persona in self._personas.items():
            raw = persona.act(state)
            weight = self._weights.get(name, 1.0)

            scaled: Dict[str, float] = {}

            # ---- choose protection layer ----
            if self.protection is not None:
                if name == "guardian":
                    layer = self.protection.guardian
                elif name == "alpha":
                    layer = self.protection.alpha
                else:
                    layer = self.protection.router
            else:
                layer = None

            try:
                # ==================================================
                # Symbol Loop
                # ==================================================
                for sym, delta in raw.items():

                    # Layer 0 — sanity on raw delta
                    delta = self._guard_numeric(name, sym, delta, "raw_delta")

                    # persona 权重
                    delta_w = self._guard_numeric(
                        name, sym, delta * weight, "weighted_delta"
                    )

                    pos = positions.get(sym, 0.0)
                    new_pos = pos + delta_w
                    increasing_risk = abs(new_pos) > abs(pos)

                    # Layer 1 — Protection scaling (may raise ReallocationRequired)
                    if layer is not None:
                        try:
                            protected_delta = layer.apply_scale(delta_w)
                        except ReallocationRequired as e:
                            self.logger(
                                f"[{name}.{sym}] protection scaling invalid → "
                                f"reallocation ({e})"
                            )
                            if self.router is not None:
                                self.router.trigger_reallocation(exclude=name)
                            scaled = {}
                            break
                        protected_delta = self._guard_numeric(
                            name, sym, protected_delta, "protected_delta"
                        )
                    else:
                        protected_delta = delta_w

                    # Layer 2 — new-risk / leverage / capacity / throughput / reference
                    if layer is not None:
                        incr_lev_est = protected_delta  # TODO: map to real leverage delta
                        allowed, msg = layer.check_new_risk(
                            current_leverage=current_leverage,
                            incremental_leverage=incr_lev_est,
                            capacity_ratio=capacity_ratio,
                            throughput_ratio=throughput_ratio,
                            reference_ratio=reference_ratio,
                        )
                        # 可选日志
                        # self.logger(f"[{name}.{sym}] protection: {msg}")

                        if not allowed and increasing_risk:
                            # risk-increasing order blocked → skip this symbol
                            continue

                    # Layer 3 — RoyalLegal bottleneck + guardian exception
                    if name == "guardian":
                        final_delta = protected_delta
                    elif increasing_risk and bottleneck < 1.0:
                        final_delta = self._guard_numeric(
                            name,
                            sym,
                            protected_delta * bottleneck,
                            "bottleneck_scale",
                        )
                    else:
                        final_delta = protected_delta

                    scaled[sym] = final_delta

            except ReallocationRequired as e:
                # ultimate safety catch
                self.logger(f"[{name}] requested reallocation: {e}")
                if self.router is not None:
                    self.router.trigger_reallocation(exclude=name)
                scaled = {}

            proposals[name] = scaled

        # ==========================================================
        # Aggregate + RoyalLegal final sanction cut
        # ==========================================================
        aggregated: Dict[str, float] = {}
        for action in proposals.values():
            for symbol, delta in action.items():
                aggregated[symbol] = aggregated.get(symbol, 0.0) + delta

        return self._royal_legal.apply(state, aggregated)
