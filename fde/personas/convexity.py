# fde/personas/convexity.py
from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from fde.personas.base import BasePersona, PersonaContext
from fde.interfaces.core import MarketSnapshot, PortfolioState


class ConvexityPersona(BasePersona):
    """
    FDE-Convexity: 宇宙凸性人格（Universe Gamma Field Projection）
    ---------------------------------------------------------------

    地球人看到的是：
        - gamma
        - convexity
        - 一个简单的 S-axis 曲线

    实际含义（你才知道）：
        - 这是 Universe Gamma Field（宇宙高维风险 curvature field）
        - 压缩到人类能看懂的一维 S-axis 投影（Projected on S-axis）
        - 属于“宇宙 → 人类近视版”的降维可视化

    输入要求：
        snapshot.options.greeks 必须包含：
            - underlying
            - gamma

    输出：
        一个 [-1, 1] 的 Series
        - 高凸性（右尾 curvature） → 越接近 +1
        - 无凸性（平坦结构） → 接近 -1
    """

    name = "FDE-Convexity"
    description = "Options convexity persona (Universe Gamma Field Projection)."

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.eps = 1e-8
        # 尾部锐化指数（sharpness > 1 → 接近 1 时更陡，宇宙右尾爆炸区）
        self.sharpness = float(self.config.get("sharpness", 2.0))

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
    ) -> pd.Series:

        # === DEBUG：允许你看到 portfolio 输入 ===
        print("\n===== PortfolioState DEBUG (ConvexityPersona) =====")
        print("Positions:\n", portfolio.positions)
        print("Equity:", portfolio.equity)
        print("Meta:", portfolio.meta)
        print("====================================================\n")

        # 没有 options / greeks → 返回 0，不影响系统
        if snapshot.options is None or snapshot.options.greeks is None:
            idx = self._default_index(snapshot, portfolio)
            return pd.Series(0.0, index=idx)

        greeks = snapshot.options.greeks

        # 必要字段缺失 → 返回 0
        required_cols = {"underlying", "gamma"}
        if not required_cols.issubset(greeks.columns):
            idx = self._default_index(snapshot, portfolio)
            return pd.Series(0.0, index=idx)

        # === Step 1: 聚合 Universe Gamma Field 的“地球版本” ===
        # 用 |gamma| 代表 convexity 绝对弯曲度
        agg = (
            greeks.assign(abs_gamma=lambda df: df["gamma"].abs())
                  .groupby("underlying")["abs_gamma"]
                  .sum()
        )

        # === Step 2: 把 convexity 对齐到 asset index ===
        idx = self._default_index(snapshot, portfolio)
        scores = agg.reindex(idx).fillna(0.0)

        # === Step 3: normalize → [0,1] ===
        if scores.max() > 0:
            scores = scores / (scores.max() + self.eps)

        # === Step 4: Tail Amplification（尾部宇宙右维 curvature 放大） ===
        scores = np.power(scores, self.sharpness)

        # === Step 5: map to [-1,1] ===
        # 低凸性: -1， 高凸性: +1
        scores = 2.0 * scores - 1.0

        return scores

    @staticmethod
    def _default_index(snapshot: MarketSnapshot, portfolio: PortfolioState) -> pd.Index:
        """
        选择 universe personalization 的资产维度 index。
        优先级：
            1) snapshot.prices.index
            2) portfolio.positions.index
        """
        if snapshot.prices is not None:
            return snapshot.prices.index
        if portfolio.positions is not None:
            return portfolio.positions.index
        return pd.Index([])
