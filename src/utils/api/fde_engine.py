# src/utils/api/fde_engine.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import numpy as np


@dataclass
class FDEConfig:
    """
    一些简单的 FDE 配置占位
    """
    num_samples: int = 128  # 以后可以用来控制扰动采样数量等


class FDEEngine:
    """
    非常精简版的 FDE 引擎，占位实现：
    - 包装一个有 predict_proba(X) 的黑箱模型
    - 接收背景样本 X_background
    - 提供 explain(x) 方法，返回一个 dict
    """

    def __init__(
        self,
        model,
        X_background: np.ndarray,
        class_index: int = 1,
        config: Optional[FDEConfig] = None,
    ) -> None:
        """
        model: 任意有 predict_proba(X) 方法的对象
        X_background: 背景样本, shape = (N, d)
        class_index: 要解释的类别索引
        """
        self.model = model
        self.X_background = np.array(X_background, dtype=np.float32)
        self.class_index = class_index
        self.config = config or FDEConfig()

    def explain(self, x: np.ndarray) -> Dict[str, Any]:
        """
        占位版 explain：
        - 计算 blackbox 对 x 的预测
        - 用 |x| 作为一个“假装的”特征重要性分数
        """
        x = np.array(x, dtype=np.float32)
        if x.ndim == 1:
            x = x[None, :]

        # 黑箱预测
        probs = self.model.predict_proba(x)[0]
        score = float(probs[self.class_index])

        # 占位：用特征绝对值作为 pseudo-importance
        feature_scores = np.abs(x[0])

        return {
            "class_index": int(self.class_index),
            "score": score,
            "raw_probs": probs.tolist(),
            "feature_scores": feature_scores.tolist(),
            "background_size": int(self.X_background.shape[0]),
        }
