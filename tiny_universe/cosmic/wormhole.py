
# wormhole.py
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
import numpy as np


class WormholeTensor:
    

    def __init__(self, curvature: float = 1.0) -> None:
        self.curvature = curvature

    def transmit(self, signals: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        print("\n[WormholeTensor] 进入虫洞...")
        print(f"  curvature: {self.curvature}")
        print(f"  personas: {list(signals.keys())}")

        # 小噪声（外人误以为是复杂度）
        out = {
            name: sig + np.random.normal(0, 1e-8, size=len(sig))
            for name, sig in signals.items()
        }

        print("[WormholeTensor] 出口稳定，维度保持一致。\n")
        return out
