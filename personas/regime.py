
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev
from typing import Any, Dict

from .base import BasePersona, MarketState


@dataclass
class RegimeConfig:
    # 哪个 feature 代表“主指数价格”，比如 price_close::SPY
    price_feature_key: str = "price_close::SPY"

    # 移动窗口（单位：步 / bars），越大越平滑
    short_window: int = 20
    long_window: int = 60
    vol_window: int = 20

    # 年化波动阈值（粗糙，但够用）
    low_vol_threshold: float = 0.15      # < 15% 年化视为“平静”
    crash_vol_threshold: float = 0.40    # > 40% 年化 + 下跌 视为“崩盘”

    # 各 regime 对应的风险倍率（给 router 用）
    regime_risk_map: Dict[str, float] | None = None

    def build_regime_risk_map(self) -> Dict[str, float]:
    """
    Regime → risk_scalar 映射（两档：满载 / 清仓）

    思路：
      - 只有 bull_trend 允许其它 personas 开满仓 (1.0)
      - 其余所有状态统一 0.0（让 router 把总仓位打到 0 = flatten）
    """
    if self.regime_risk_map is not None:
        return self.regime_risk_map

    return {
        "warmup": 0.0,      # 样本不足，不下场
        "bull_trend": 1.0,  # 满载仓位
        "bear_trend": 0.0,  # 直接平仓 / 不持仓
        "sideways": 0.0,    # 不参与，等结构清晰再说
        "crash": 0.0,       # 强制清仓，等 Guardian 决定何时再进
    }


class RegimePersona(BasePersona):
    """
    RegimePersona: 基于“移动步长律”的市场状态检测器。

    逻辑：
    - 维护一段价格 history（deque），每一步更新一次；
    - 计算短期 / 长期移动平均 (short_window / long_window)；
    - 计算 rolling 实际波动率 (vol_window) 并粗略年化；
    - 用简单 rule-based law 决定当前 regime：
        - crash: 年化波动大 + 刚刚一步是大跌
        - bull_trend: 短均线 > 长均线 且 波动低
        - bear_trend: 短均线 < 长均线 且 波动低
        - sideways: 其余情况

    输出:
    - act(...) 返回空 dict（不直接下单）；
    - 把当前 regime 与 risk_scalar 暴露在:
        - self.current_regime
        - self.current_risk_scalar
      由 SovereignRouter / Kernel 读取后，对别的 personas 的仓位统一缩放。
    """

    name = "regime"

    def __init__(self, config: Dict[str, Any] | None = None):
        cfg = RegimeConfig(**(config or {}))

        self.config = cfg
        self.price_feature_key = cfg.price_feature_key
        self.short_window = cfg.short_window
        self.long_window = cfg.long_window
        self.vol_window = cfg.vol_window
        self.low_vol_threshold = cfg.low_vol_threshold
        self.crash_vol_threshold = cfg.crash_vol_threshold
        self.regime_risk_map = cfg.build_regime_risk_map()

        # history 只存价格，长度取最大窗口
        max_len = max(self.long_window, self.vol_window + 1)
        self._price_history: deque[float] = deque(maxlen=max_len)

        # 这两项是“状态输出”，给上层读
        self.current_regime: str = "warmup"
        self.current_risk_scalar: float = 0.0

    # ---------- 内部工具 ----------

    def _update_history(self, price: float) -> None:
        self._price_history.append(float(price))

    def _has_enough_history(self) -> bool:
        needed = max(self.long_window, self.vol_window + 1)
        return len(self._price_history) >= needed

    def _compute_short_long_ma(self) -> tuple[float, float]:
        prices = list(self._price_history)
        short_ma = mean(prices[-self.short_window:])
        long_ma = mean(prices[-self.long_window:])
        return short_ma, long_ma

    def _compute_annualized_vol_and_last_ret(self) -> tuple[float, float]:
        prices = list(self._price_history)
        rets = [
            prices[i] / prices[i - 1] - 1.0
            for i in range(1, len(prices))
        ]

        window_rets = rets[-self.vol_window:]
        if len(window_rets) <= 1:
            return 0.0, 0.0

        # population std dev; 再粗略年化成日频~252
        vol = pstdev(window_rets) * sqrt(252.0)
        last_ret = window_rets[-1]
        return vol, last_ret

    def _infer_regime(self) -> str:
        if not self._has_enough_history():
            return "warmup"

        short_ma, long_ma = self._compute_short_long_ma()
        vol, last_ret = self._compute_annualized_vol_and_last_ret()

        # 1. 崩盘：波动极高 + 刚刚一步是大跌
        if vol >= self.crash_vol_threshold and last_ret < 0:
            return "crash"

        # 2. 牛趋势：短均线向上穿/在上，且波动不高
        if short_ma > long_ma and vol <= self.low_vol_threshold:
            return "bull_trend"

        # 3. 熊趋势：短均线在长均线下方，波动不高
        if short_ma < long_ma and vol <= self.low_vol_threshold:
            return "bear_trend"

        # 4. 其余情况视为震荡 / 结构不清晰
        return "sideways"

    def _update_outputs(self) -> None:
        regime = self._infer_regime()
        self.current_regime = regime
        self.current_risk_scalar = self.regime_risk_map.get(regime, 1.0)

    # ---------- Persona 接口 ----------

    def act(self, state: MarketState) -> Dict[str, float]:
        # 从 features 里抓“主指数价格”
        price = state.features.get(self.price_feature_key)
        if price is None:
            # 没有价格信息，保持上一次 regime 与 risk_scalar，不强行动
            return {}

        self._update_history(price)
        self._update_outputs()

        # RegimePersona 不直接下单，只给上层提供 risk_scalar
        # 由 SovereignRouter / Kernel 读取:
        #   regime = regime_persona.current_regime
        #   scalar = regime_persona.current_risk_scalar
        return {}
