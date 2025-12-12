import pandas as pd
from typing import Dict, Any


class ToyPersona:
    """
    极简 Persona：
    - 输入 snapshot / portfolio / ctx / factors
    - 输出一个 1D signal Series
    """

    def __init__(self, name: str = "toy-alpha") -> None:
        self.name = name

    def step(
        self,
        snapshot: Dict[str, Any],
        portfolio: Dict[str, Any],
        ctx: Dict[str, Any],
        factors: Dict[str, Any] | None = None,
    ) -> pd.Series:
        """
        这里我们搞一个最简单的逻辑：
        - snapshot["prices"] 是一个 {ticker: price} 的 dict
        - signal = (price - mean) / std  得到一个 z-score
        """
        prices_dict = snapshot.get("prices", {})
        if not prices_dict:
            # 没有数据就给一个空的 Series
            return pd.Series(dtype=float)

        prices = pd.Series(prices_dict, dtype=float)

        if prices.std() == 0:
            # 全部相等就给 0
            z = prices * 0.0
        else:
            z = (prices - prices.mean()) / prices.std()

        # 让 signal 更温和一点
        signal = z.clip(-2, 2) / 2.0

        return signal
