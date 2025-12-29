# src/llm/llm_engine.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


class LLMEngine:
    """
    现在的版本非常简单：

    - 初始化时接收：
        model: 任何有 predict_proba(x) 的黑箱模型
        background: 背景样本 (np.ndarray 或 list[list[float]])

    - explain(x0, meta):
        做一个最简单的“解释”占位实现：
        * 把 x0 变成 numpy
        * 调用 model.predict_proba
        * 把结果打包成一个 dict 返回
    """

    def __init__(self, model: Any, background: Any):
        self.model = model
        # 背景样本目前先存起来，后面接 FDEEngine 再用
        self.background = np.array(background)

    def explain(self, x0: List[float], meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        最简版解释函数，占位用：
        - 只调用 predict_proba
        - 返回一个 dict，给 API 直接透传
        """
        meta = meta or {}

        # x0 → (1, n_features)
        x = np.array(x0, dtype=float).reshape(1, -1)

        # 假设是二分类模型：predict_proba -> [ [p0, p1] ]
        probs = self.model.predict_proba(x)[0].tolist()

        return {
            "x0": x0,
            "probs": probs,
            "meta": meta,
        }
