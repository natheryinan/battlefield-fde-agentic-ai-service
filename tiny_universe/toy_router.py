

from __future__ import annotations

from typing import Mapping
import pandas as pd


class ToyEqualWeightRouter:
    

    def route(self, signals: Mapping[str, pd.Series]) -> pd.Series:
        if not signals:
            raise ValueError("ToyEqualWeightRouter.route: no signals provided.")

        df = pd.DataFrame(signals)

        
        final = df.mean(axis=1)

        final.name = "final_signal"
        return final


__all__ = ["ToyEqualWeightRouter"]
