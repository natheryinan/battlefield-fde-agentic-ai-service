# architecture/data_contracts.py

from dataclasses import dataclass, field
from typing import Dict, Any, List


# ===== 核心行情快照 =====

@dataclass
class MarketSnapshot:
    """
    Canonical market state at a given timestamp.

    这里保持干净：
    - symbols: List[str]
    - prices: Dict[str, float]
    - extra:  任意补充信息（数据源 tag、session id 等）

    脏数据的纠偏由 engine.normalizer 完成，这里只接“正常形”。
    """
    timestamp: float
    symbols: List[str]
    prices: Dict[str, float]
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 永远保证 extra 是 dict，不允许 None 漏进来
        if self.extra is None:
            self.extra = {}


# ===== 特征快照 + LIKE TYPES + 变幻方程 =====

@dataclass
class FeatureSnapshot:
    """
    Derived features at a given timestamp, tied to symbols.

    除了基本的 features / extra 以外，这里挂上两块新约束：
    - like_types:       类型形状说明（LIKE TYPES / 类型值）
    - transform_specs:  特征的变幻方程说明（equation / inputs / params）

    这两个字段可以由：
    - 引擎 ingest 时构造并往下传
    - 或由 FeaturesBuilder 在 build 过程中补充 / 覆盖
    """
    timestamp: float
    symbols: List[str]
    features: Dict[str, Any]

    # 普通扩展信息（比如 data source、regime tag 等）
    extra: Dict[str, Any] = field(default_factory=dict)

    # === 类型值 / LIKE TYPES ===
    like_types: Dict[str, Any] = field(default_factory=dict)

    # === 变幻方程 ===
    transform_specs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 这三个都永远保持 dict，不允许 None 穿透
        if self.extra is None:
            self.extra = {}
        if self.like_types is None:
            self.like_types = {}
        if self.transform_specs is None:
            self.transform_specs = {}
