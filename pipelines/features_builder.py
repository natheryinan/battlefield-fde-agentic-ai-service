

# pipeline/features_builder.py

from typing import Dict, Any
import numpy as np


class FeaturesBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config

    def compute_basic_features(self, prices):
        if len(prices) > 1:
            ret_1 = prices[-1] / prices[-2] - 1
        else:
            ret_1 = 0.0

        window = self.cfg.get("vol_window", 20)
        if len(prices) >= 2:
            vol_window = float(np.std(prices[-window:]))
        else:
            vol_window = 0.0

        return {
            "ret_1": ret_1,
            "vol_window": vol_window,
        }

    def build(self, raw_batch) -> Dict[str, Any]:
        payload = raw_batch.payload
        prices = payload.get("prices", {})
        # prices 是 dict[str, float]，拿 value 列表
        price_list = list(prices.values())

        features = self.compute_basic_features(price_list)

        return {
            "timestamp": payload.get("timestamp", raw_batch.timestamp),
            "symbols": payload.get("symbols", []),
            "features": features,
            # 保留原始 extra / like_types / transform_specs 给上层
            "extra": {
                "source_extra": payload.get("extra", {}),
                "like_types": payload.get("_like_types", {}),
                "transform_specs": payload.get("_transform_specs", {}),
            },
        }
