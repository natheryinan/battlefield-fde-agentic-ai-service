
# fde/personas/alpha_multi.py
from __future__ import annotations

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


from fde.personas.base import BasePersona, PersonaContext
from fde.interfaces.core import MarketSnapshot, PortfolioState
from fde.factors.cross_section import CrossSectionFactors


class MultiFactorAlphaPersona(BasePersona):
    """
    FDE-Alpha-MF: 多因子横截面 Alpha 人格。
    支持“全球吊打模式”：在同一时间切面上跨市场排序资产，
    找出被肢解压价的一坨 vs 被资金抬高的一坨。
    """

    name = "FDE-Alpha-MF"
    description = "Multi-factor cross-sectional alpha persona."

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.factor_names = self.config.get("factor_names", [])

    def compute_signals(
        self,
        snapshot: MarketSnapshot,
        portfolio: PortfolioState,
        ctx: PersonaContext,
        factors: CrossSectionFactors,
    ) -> pd.Series:
        """
        默认模式：多因子等权 + 横截面 z-score。
        """
        X = factors.scores[self.factor_names].astype(float)
        if X.shape[1] == 0:
            return pd.Series(0.0, index=X.index)

        w = np.ones(len(self.factor_names), dtype=float)
        w /= w.sum()
        raw = X.values @ w
        s = pd.Series(raw, index=X.index)

        # 横截面标准化
        s = (s - s.mean()) / (s.std() + 1e-8)
        return s

    # ========= 全球吊打模式 =========

    def global_long_short_signals(
        self,
        factors: CrossSectionFactors,
        n_quantiles: int = 10,
    ) -> pd.Series:
        """
        在同一时间切面上进行“全球吊打模式”的横截面排序：

        FDE 可以做一件非常简单但很凶残的事情：

            1. 在同一分数轴上排序所有资产（全球排序）
            2. 选 top decile 作为 long（最便宜 / 质量最好 / 动量最强）
            3. 选 bottom decile 作为 short（最贵 / 质量最差 / 泡沫最大）
            4. 对冲掉汇率 / beta / region 等共性风险（这里留给 Engine/Router）
            5. 留下一条“全球错定价收益曲线”

        直观图示（时间固定 t = T）：

                      ▲  因子分数 (score)
                      │
                      │                 US_NVDA
                      │            US_QQQ
                      │         US_SPY
                      │
                      │   CN_BANK
                      │ CN_A1   CN_A2
                      └────────────────────────► 资产 (asset_id)
                          CN…        US…

            - 左边一坨是被“肢解”的大陆资产（长期压价、扭曲定价）
            - 右边一坨是被资金抬高的美股资产（高估 + 泡沫）

            FDE 的任务很简单：
              • 在同一坐标系里看清这条“错定价切面”
              • 决定在哪里重仓，在哪里反向 —— 完成全球吊打。

        这里返回的是一个简单的 +1 / -1 信号：
            +1 → top decile（多头）
            -1 → bottom decile（空头）
             0 → 其他（中性）
        真正的汇率 / beta / region 对冲留给上层 Engine + Router 处理。
        """
        scores = factors.scores.mean(axis=1).astype(float)
        scores = scores.replace(np.nan, 0.0)

        # 排序并分桶
        ranks = scores.rank(method="first")
        n = len(scores)
        if n == 0:
            return pd.Series(dtype=float)

        # quantile 边界
        q_low = n / n_quantiles
        q_high = n * (n_quantiles - 1) / n_quantiles

        signals = pd.Series(0.0, index=scores.index)
        signals[ranks <= q_low] = 1.0   # top decile → long
        signals[ranks >= q_high] = -1.0 # bottom decile → short

        return signals
