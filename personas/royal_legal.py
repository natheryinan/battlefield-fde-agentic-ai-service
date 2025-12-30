# engine/royal_legal.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Union

from personas.base import MarketState


Number = Union[int, float]


@dataclass
class RoyalLegalConfig:
    """
    ROYAL LEGAL 全局配置 + 惩戒窗口参数：
    """
    # 风险分段
    risk_soft: float = 0.2
    risk_medium: float = 0.45
    risk_hard: float = 0.7

    # 在各个分段下砍掉的目标仓位比例
    cut_low: float = 0.0     # 低风险：不砍
    cut_mid: float = 0.65    # 中风险：砍掉 65%
    cut_high: float = 1.0    # 高风险：砍掉 100%
    cut_max: float = 1.0     # 极高风险：砍掉 100%（平掉目标仓）

    # 制裁 / 封锁时是否直接平仓
    sanction_flatten: bool = True

    # 惩戒锁仓窗口长度（单位和 timestamp 一致，比如 bar 数 / 秒）
    lock_window: float = 5.0

    # 违纪分数自然衰减速度（每单位时间减少多少）
    violation_decay_rate: float = 0.37


@dataclass
class LegalRestraints:
    """
    额外类：专门管理“法律 + 时间的约束”：

    - violation_score：违纪严重程度
    - last_update_ts：上次更新时间
    - lock_until_ts：惩戒锁仓窗口的 end time
    - hard_freeze：
        一旦发生重度违纪（制裁 / 极端砍仓），在 lock_window 内：
          -> hard_freeze = True
          -> 不再允许任何“加风险”的动作（瓶颈直接=0）
          -> 只允许减仓 / 对冲
    """

    cfg: RoyalLegalConfig
    violation_score: float = 0.0
    last_update_ts: Optional[float] = None
    lock_until_ts: Optional[float] = None
    hard_freeze: bool = False

    # ------ 时间自然衰减 ------
    def apply_time_decay(self, now_ts: Optional[float]) -> None:
        if now_ts is None or self.last_update_ts is None:
            self.last_update_ts = now_ts
            return

        dt = max(0.0, now_ts - self.last_update_ts)
        if dt <= 0.0:
            return

        decay = self.cfg.violation_decay_rate * dt
        self.violation_score = max(0.0, self.violation_score - decay)
        self.last_update_ts = now_ts

    # ------ 违纪事件更新 + 锁仓窗口 ------
    def update_on_event(
        self,
        combined_risk: float,
        risk_cut: float,
        had_sanction_event: bool,
        now_ts: Optional[float],
    ) -> None:
        """
        - sanction / 极端砍仓：重度违纪
            -> violation_score +2
            -> hard_freeze = True
            -> lock_until_ts = now_ts + lock_window（惩戒 end time）
        - 中度砍仓：violation_score +1
        """
        v = self.violation_score

        if had_sanction_event or risk_cut >= self.cfg.cut_high:
            v += 2.0
            if now_ts is not None:
                lock_end = now_ts + self.cfg.lock_window
                # 启动或延长锁仓窗口
                if self.lock_until_ts is None:
                    self.lock_until_ts = lock_end
                else:
                    self.lock_until_ts = max(self.lock_until_ts, lock_end)
            self.hard_freeze = True

        elif risk_cut >= self.cfg.cut_mid:
            v += 1.0

        # 限在 [0,20]
        self.violation_score = max(0.0, min(v, 20.0))

        # 如果已经过了锁仓窗口，解除硬冻结
        if now_ts is not None and self.lock_until_ts is not None:
            if now_ts >= self.lock_until_ts:
                self.hard_freeze = False
                self.lock_until_ts = None

    # ------ 对外：给 ALPHA 的瓶颈函数 ------
    def bottleneck_factor(self, current_ts: Optional[float] = None) -> float:
        """
        瓶颈方程（带惩戒 end time & hard_freeze）：

        - 如果 hard_freeze=True 且未出锁仓窗口：
              -> 返回 0.0（完全不许加风险）
        - 否则：
              使用违纪分数去塑形：
                  v = violation_score
                  k = 0.3
                  f = 1 / (1 + k * v)
              然后夹在 [0.15, 1.0] 之间。
        """
        # 先更新硬冻结状态（时间到则自动解冻）
        if current_ts is not None and self.lock_until_ts is not None:
            if current_ts >= self.lock_until_ts:
                self.hard_freeze = False
                self.lock_until_ts = None

        # ALPHA 已经用刀砍过一次且仍在窗口内 → 不准再加风险（瓶颈=0）
        if self.hard_freeze and (
            self.lock_until_ts is None
            or (current_ts is not None and current_ts < self.lock_until_ts)
        ):
            return 0.0

        # 正常违纪瓶颈形状
        v = self.violation_score
        k = 0.3
        f = 1.0 / (1.0 + k * v)
        return max(0.15, min(1.0, f))


class RoyalLegalOverlay:
    """
    ROYAL LEGAL 容器 👑⚖️

    - 对聚合后的 delta 做惩戒式截断 / 平仓
    - 内部委托 LegalRestraints 管理：
        * 违纪分数
        * 惩戒锁仓 end time
        * hard_freeze（ALPHA 用刀后，本窗口内“不准再加风险”）
    """

    def __init__(self, config: RoyalLegalConfig | None = None):
        self.config = config or RoyalLegalConfig()
        self._restraints = LegalRestraints(self.config)

    # -----------------------------
    # 对外：给 ALPHA 调用的瓶颈函数
    # -----------------------------
    def current_bottleneck_factor(self, current_ts: Optional[float] = None) -> float:
        return self._restraints.bottleneck_factor(current_ts=current_ts)

    # -----------------------------
    # 对外主接口：应用截断
    # -----------------------------
    def apply(
        self,
        state: MarketState,
        proposed_delta: Dict[str, float],
    ) -> Dict[str, float]:
        cfg = self.config

        # 解析时间戳：支持 state.timestamp / state.time
        now_ts = self._extract_timestamp(state)

        # 时间自然衰减
        self._restraints.apply_time_decay(now_ts)

        # 当前仓位
        positions: Dict[str, float] = getattr(state, "positions", {}) or {}
        if not positions:
            return proposed_delta

        symbols = set(positions.keys()) | set(proposed_delta.keys())

        # --- 法律风险 ---
        legal_risk = float(getattr(state, "legal_risk_score", 0.0) or 0.0)
        litigation_risk = float(getattr(state, "litigation_risk_score", 0.0) or 0.0)
        legal_risk = max(0.0, min(legal_risk, 1.0))
        litigation_risk = max(0.0, min(litigation_risk, 1.0))
        combined_risk = max(legal_risk, litigation_risk)

        # --- 制裁 / 封锁 ---
        global_sanction_flag: bool = bool(getattr(state, "sanction_flag", False))
        per_symbol_sanctions: Dict[str, bool] = getattr(state, "sanction_flags", {}) or {}
        jurisdiction_blocked: bool = bool(getattr(state, "jurisdiction_blocked", False))

        # 无风险、无制裁：只做时间衰减，不增违纪分
        if (
            combined_risk == 0.0
            and not global_sanction_flag
            and not jurisdiction_blocked
            and not any(per_symbol_sanctions.values())
        ):
            self._restraints.update_on_event(
                combined_risk=combined_risk,
                risk_cut=0.0,
                had_sanction_event=False,
                now_ts=now_ts,
            )
            return proposed_delta

        risk_cut = self._risk_cut_ratio(combined_risk, cfg)

        final_delta: Dict[str, float] = {}
        had_sanction_event = False

        for sym in symbols:
            pos = positions.get(sym, 0.0)
            base_delta = proposed_delta.get(sym, 0.0)
            proposed_new_pos = pos + base_delta

            # 1) 制裁 / 封锁优先：一刀平仓
            if self._should_flatten_symbol(
                symbol=sym,
                global_sanction_flag=global_sanction_flag,
                per_symbol_sanctions=per_symbol_sanctions,
                jurisdiction_blocked=jurisdiction_blocked,
                cfg=cfg,
            ):
                final_delta[sym] = -pos
                had_sanction_event = True
                continue

            # 2) 法律风险砍仓：
            if risk_cut <= 0.0:
                final_delta[sym] = base_delta
                continue

            target_pos = proposed_new_pos * (1.0 - risk_cut)
            delta_after_legal = target_pos - pos
            final_delta[sym] = delta_after_legal

        # 更新违纪分数 + 惩戒窗口 / hard_freeze
        self._restraints.update_on_event(
            combined_risk=combined_risk,
            risk_cut=risk_cut,
            had_sanction_event=had_sanction_event,
            now_ts=now_ts,
        )

        return final_delta

    # -----------------------------
    # 内部：是否对某个 symbol 直接平仓
    # -----------------------------
    def _should_flatten_symbol(
        self,
        symbol: str,
        global_sanction_flag: bool,
        per_symbol_sanctions: Dict[str, bool],
        jurisdiction_blocked: bool,
        cfg: RoyalLegalConfig,
    ) -> bool:
        if not cfg.sanction_flatten:
            return False

        if jurisdiction_blocked:
            return True

        if per_symbol_sanctions.get(symbol, False):
            return True

        if global_sanction_flag:
            return True

        return False

    # -----------------------------
    # 内部：combined_risk -> “砍仓比例”
    # -----------------------------
    def _risk_cut_ratio(self, combined_risk: float, cfg: RoyalLegalConfig) -> float:
        if combined_risk >= cfg.risk_hard:
            return cfg.cut_max
        if combined_risk >= cfg.risk_medium:
            return cfg.cut_high
        if combined_risk >= cfg.risk_soft:
            return cfg.cut_mid
        return cfg.cut_low

    # -----------------------------
    # 时间戳提取
    # -----------------------------
    def _extract_timestamp(self, state: MarketState) -> Optional[float]:
        raw: Optional[Union[Number, datetime]] = getattr(state, "timestamp", None)
        if raw is None:
            raw = getattr(state, "time", None)

        if raw is None:
            return None

        if isinstance(raw, datetime):
            return raw.timestamp()

        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
