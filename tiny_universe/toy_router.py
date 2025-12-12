

from __future__ import annotations

from typing import Mapping
import pandas as pd


class ToyEqualWeightRouter:
    

    def route(self, signals: Mapping[str, pd.Series]) -> pd.Series:
        if not signals:
            raise ValueError("ToyEqualWeightRouter.route: no signals provided.")

        df = pd.DataFrame(signals)

    import pandas as pd
from typing import Dict, Any


class ToyRouter:
    """
    极简 Router：
    - persona_outputs: {name: pd.Series}
    - 输出：所有 persona signal 的平均
    """

    def __call__(
        self,
        persona_outputs: Dict[str, pd.Series],
        ctx: Dict[str, Any],
    ) -> pd.Series:
        if not persona_outputs:
            return pd.Series(dtype=float)

        # 对齐 index 后取平均
        df = pd.DataFrame(persona_outputs)
        return df.mean(axis=1)

        final = df.mean(axis=1)

        final.name = "final_signal"
        return final


__all__ = ["ToyEqualWeightRouter"]
