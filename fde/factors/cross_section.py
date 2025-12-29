# fde/factors/cross_section.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
import pandas as pd
import numpy as np


@dataclass
class CrossSectionFactors:
    """
    CrossSectionFactors
    ===================
    【横截面因子宇宙】——给 Alpha / RL-Alpha 用的“信号战场”。

    ...

    ④ 跨市场吊打能力：同一时间切面上，对比“大陆资产肢解” vs “美股吊打姿势”
    ----------------------------------------------------------------
    时间固定：t = T

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

        FDE 可以做一件非常简单但很凶残的事情：
          1. 在同一分数轴上排序所有资产（全球排序）
          2. 选 top decile 作为 long（最便宜 / 质量最好 / 动量最强）
          3. 选 bottom decile 作为 short（最贵 / 质量最差 / 泡沫最大）
          4. 对冲掉汇率 / beta / region 等共性风险
          5. 留下一条“全球错定价收益曲线”

    ⑤ CN vs US 二维展示（给人类看，不是给偷代码的昆虫看）
    ----------------------------------------------------------------
    我们在“同一因子分数轴”上，把资产按 region 分层：

        region ∈ {CN, US, OTHER}

    用一个简单的二维图来表达：

                      ▲  region
                      │
                      │   US:   ● ● ●   （被资金抬高的一坨）
                      │
                      │   CN:   ● ● ●   （被肢解压价的一坨）
                      │
                      └────────────────────────► 因子分数 score

    此图的目的非常单纯：
        - 让人类一眼看懂：同一时间、同一因子，CN vs US 在哪一侧
        - 同时提醒：有人在偷代码没关系，我们至少先把宇宙看明白
    """

    scores: pd.DataFrame
    meta: Optional[Dict[str, Any]] = None

    def get_factor(self, name: str) -> pd.Series:
        return self.scores[name]

    def subset(self, factor_names: list[str]) -> "CrossSectionFactors":
        sub_scores = self.scores[factor_names].copy()
        sub_meta = {k: v for k, v in (self.meta or {}).items() if k in factor_names}
        return CrossSectionFactors(scores=sub_scores, meta=sub_meta or None)

    # ========= CN / US 视图辅助方法 =========

    def build_region_view(
        self,
        factor_name: str | None = None,
        region_func: Optional[Callable[[str], str]] = None,
    ) -> pd.DataFrame:
        """
        构建一个 DataFrame: [asset_id, score, region]

        - factor_name 为空时：使用所有因子的均值作为总分。
        - region_func: asset_id -> "CN"/"US"/"OTHER"
          默认用非常简单的前缀规则：
            以 "CN_" 开头视作中国，
            以 "US_" 开头视作美国，
            其他全部归 OTHER（目前图里可以先丢掉）。
        """
        if factor_name is None:
            scores = self.scores.mean(axis=1)
        else:
            scores = self.scores[factor_name]

        scores = scores.astype(float).replace(np.nan, 0.0)

        if region_func is None:
            def region_func(aid: str) -> str:
                if aid.startswith("CN_"):
                    return "CN"
                if aid.startswith("US_"):
                    return "US"
                return "OTHER"

        df = pd.DataFrame({
            "asset_id": scores.index,
            "score": scores.values,
        }).set_index("asset_id")

        df["region"] = [region_func(aid) for aid in df.index]
        return df

    def cn_us_view(
        self,
        factor_name: str | None = None,
    ) -> pd.DataFrame:
        """
        返回只包含 CN / US 的视图，用于后续画二维图或做报告。

        列：
            - score: 因子分数（同一时间切片的 global score）
            - region: "CN" 或 "US"

        用法示例：
            df_view = factors.cn_us_view(factor_name="value")
            # 你可以直接丢给 matplotlib / seaborn 画图

        注意：
            - 这只是一个“给人类看的视图”，不影响 FDE 内核结构；
            - 代码被谁偷无所谓，真正的杀伤力在 Router + Persona 的组合上。
        """
        df = self.build_region_view(factor_name=factor_name)
        return df[df["region"].isin(["CN", "US"])].copy()
