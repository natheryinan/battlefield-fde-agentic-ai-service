
# fde/interfaces/factors.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd


@dataclass
class CrossSectionFactors:
    """
    CrossSectionFactors
    ===================
    【横截面因子宇宙】——给 Alpha / RL-Alpha 用的“信号战场”。

    ----------------------------------------------------------------------
    作用（复习）：
        • 做横截面因子
        • 做趋势 / mean reversion
        • 做 RL reward
    ----------------------------------------------------------------------

    一、为什么要把“横截面因子”对象化？（对象化捕捉）
    ----------------------------------------------------------------------
    1. 统一资产维度
       - scores: index = asset_id, columns = factor_name
       - 所有人格（Alpha / RL / Liquidity）都从同一个矩阵读因子
       - 避免在各处散落 DataFrame / dict

    2. 可组合、可复用
       - 可以在这里做线性 / 非线性组合，生成“综合战斗力因子”
       - 因子可以打标签：style, horizon, regime 等，方便 Router 挑选

    3. 内置元信息（meta）
       - 保存因子暴露、IC、turnover、robustness 等指标
       - 让 Guardian / Router 可以根据“因子健康度”调权

    ----------------------------------------------------------------------
    二、为什么“横截面因子”在 FDE 里能吊打很多原始价差信号？
    ----------------------------------------------------------------------
    ① 维度扩展优势（multi-asset, cross-section）
       - 单资产时间序列信号，只能在一条时间线里博弈
       - 横截面因子在同一时间切片上比较 N 只资产 → 更高的信息密度
       - 用同一货币（score）比较谁贵谁便宜，who is mispriced NOW

    ② 可中性化 / 可控风险（neutralization）
       - 可以对行业、市值、beta、风格做中性化
       - 让 alpha 更接近“纯错定价”，而不是宏观/大盘噪音
       - Guardian 容易评估风险，因为暴露是结构化的

    ③ 统计稳定性强（statistical robustness）
       - 每个时间点都可以在横截面上做一次实验（N 维样本）
       - 有利于估计因子 IC、t-stat、检验稳定性
       - 相比单一时间序列，收敛更快、可检验性更强

    ④ 直接给 RL 做 reward shaping
       - RL 可以用“横截面排序收益”作为 reward：
         排名靠前资产收益 > 排名靠后资产 → reward > 0
       - 避免 RL 直接在 noisy PnL 上学习，收敛更快、更稳
       - 也能按因子暴露定制 penalty（比如过度集中、过度杠杆）

    ⑤ 容易与 Convexity / Guardian 对接
       - Convexity 人格可以在因子空间上挑选“对尾部敏感的资产”
       - Guardian 可以根据因子集中度 / Gini 来降权：
         因子过度集中 → 系统性风险高 → 降低全局杠杆

    ----------------------------------------------------------------------
    三、FDE 战争系统中的位置（结构图）
    ----------------------------------------------------------------------

        价格 / 特征数据                     组合 & 风控
        ┌────────────────────┐           ┌────────────────┐
        │   MarketSnapshot   │           │ PortfolioState  │
        │  prices / ohlcv    │           │ positions ...   │
        └─────────┬──────────┘           └────────┬───────┘
                  │                               │
                  │ 构造横截面因子                 │
                  ▼                               │
        ┌────────────────────┐                    │
        │ CrossSectionFactors│                    │
        │  scores: N×K 矩阵   │                    │
        └─────────┬──────────┘                    │
                  │                               │
        ┌─────────▼──────────┐          ┌────────▼────────┐
        │   Alpha / RL-Alpha  │          │   Guardian      │
        │   生成 signals      │          │   生成 scaler   │
        └─────────┬──────────┘          └────────┬────────┘
                  │                               │
                  └──────────┬──────────┬─────────┘
                             ▼
                      ┌───────────────┐
                      │ PersonaRouter │
                      │   融合信号    │
                      └───────────────┘

    ----------------------------------------------------------------------
    四、接口定义
    ----------------------------------------------------------------------
    """

    # 因子得分矩阵：
    #   index: asset_id
    #   columns: factor 名，例如 ["value","quality","momentum","carry",...]
    scores: pd.DataFrame

    # 可选：每个因子的元信息（IC、半衰期、风格标签等）
    #   例如：
    #   meta = {
    #       "value": {"style": "value", "horizon": "long", "ic": 0.04},
    #       "momentum": {"style": "trend", "horizon": "medium", "ic": 0.06},
    #   }
    meta: Optional[Dict[str, Any]] = None

    def get_factor(self, name: str) -> pd.Series:
        """
        取出单个因子向量，方便 Alpha 人格直接使用。
        """
        return self.scores[name]

    def subset(self, factor_names: list[str]) -> "CrossSectionFactors":
        """
        只保留指定的若干因子，返回一个新的 CrossSectionFactors。
        """
        sub_scores = self.scores[factor_names].copy()
        sub_meta = {k: v for k, v in (self.meta or {}).items() if k in factor_names}
        return CrossSectionFactors(scores=sub_scores, meta=sub_meta or None)
