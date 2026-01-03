from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class RouterState:
    """
    Router runtime 状态：
    - dynamic_weights: 当前 tick 生效的路由权重（已经叠加 multiplier 并归一化）
    - multipliers: 每条腿的放大倍数（在出事时逐渐加重）
    - excluded_personas: 当前 tick 被踢出路由的 personas
    - degrade_mode: 是否已经进入“拉垮后”的降级模式
    - commentary: 一句简短说明，方便日志和监控
    """
    dynamic_weights: Dict[str, float] = field(default_factory=dict)
    multipliers: Dict[str, float] = field(default_factory=dict)
    excluded_personas: Set[str] = field(default_factory=set)

    degrade_mode: bool = False
    commentary: str = ""


class SovereignRouter:
    """
    渐进式权重路由器：

    - base_weights: 初始权重（可认为是平衡状态的“静态解”）
    - multipliers: 对 base_weights 的动态放大倍数
    - 每当某条腿（persona）失效：
        1) 设为 multiplier=0，并加入 excluded 集合
        2) 对剩余腿： multiplier *= (1 + step)（上限 max_multiplier）
        3) 计算 load = Σ base_weight * multiplier
           - 若 load 未超过 collapse_threshold → 只是“更偏”的解
           - 若 load 超过 collapse_threshold → 认为方程被拉垮，进入降级模式
    """

    def __init__(
        self,
        base_weights: Dict[str, float],
        logger=None,
        step: float = 0.25,          # 每次 reallocation 时乘以 (1 + step)
        max_multiplier: float = 3.0, # 单腿最大放大倍数
        collapse_threshold: float = 2.0,  # 负载拉垮阈值: 相对 base 的倍数
        guardian_name: str = "guardian",
        liquidity_name: str = "liquidity",
    ):
        # 归一化 base_weights，保证起始 sum=1，更好解释“倍数”
        total = sum(max(0.0, w) for w in base_weights.values())
        if total <= 0:
            raise ValueError("base_weights must have positive sum")

        self._base: Dict[str, float] = {
            k: max(0.0, v) / total for k, v in base_weights.items()
        }

        self.step = step
        self.max_multiplier = max_multiplier
        self.collapse_threshold = collapse_threshold
        self.guardian_name = guardian_name
        self.liquidity_name = liquidity_name

        self.logger = logger or print

        # 初始化状态：所有 multiplier=1.0
        multipliers = {k: 1.0 for k in self._base.keys()}
        self._state = RouterState(
            dynamic_weights=dict(self._base),
            multipliers=multipliers,
            excluded_personas=set(),
            degrade_mode=False,
            commentary="Initialized with base weights.",
        )

    # ==============================================================
    # 🔥 核心：渐进加重 + 拉垮检测 + reallocation
    # ==============================================================

    def trigger_reallocation(self, exclude: str):
        """
        某 persona 抛出 ReallocationRequired 或被判定数值崩坏时调用：

        - 把该 persona 从有效集合中排除（multiplier=0）
        - 对剩余 personas multiplier *= (1 + step)，上限 max_multiplier
        - 计算 load = Σ base_weight * multiplier
            - 若 load < collapse_threshold → 正常偏置下继续
            - 若 load >= collapse_threshold → 触发“方程拉垮”降级模式
        """
        if exclude not in self._state.multipliers:
            # 未知 persona，直接忽略
            return

        # 标记为排除 & multiplier 归零
        self._state.excluded_personas.add(exclude)
        self._state.multipliers[exclude] = 0.0

        self.logger(f"[Router] Persona '{exclude}' excluded → ramping others.")

        # 对剩余一下子加重：multiplier *= (1 + step)，但不超过 max_multiplier
        for name, m in list(self._state.multipliers.items()):
            if name in self._state.excluded_personas:
                continue
            boosted = m * (1.0 + self.step)
            self._state.multipliers[name] = min(boosted, self.max_multiplier)

        # 计算当前“负载”：base_weight * multiplier 的和（尚未归一化）
        load = sum(self._base[k] * self._state.multipliers[k] for k in self._base.keys())

        # 记录一下负载和 multiplier 便于 debug
        self.logger(
            f"[Router] multipliers={self._state.multipliers} | load={load:.3f}"
        )

        # 检查是否已经拉垮
        if load >= self.collapse_threshold:
            self._enter_collapse_mode(load)
        else:
            # 正常情况下，对未排除腿做一次归一化，生成当前 tick 可用权重
            self._renormalize_active(load)

    # ==============================================================

    def _enter_collapse_mode(self, load: float):
        """
        方程被拉垮：说明剩余 personas 的累积权重负载已经失衡。
        这里进入“降级模式”：
        - 优先保留 guardian / liquidity，两腿平分或按 base ratio 分配
        - 其他 personas 直接权重清零
        """
        self.logger(
            f"[Router] Load {load:.3f} >= collapse_threshold={self.collapse_threshold:.3f} "
            f"→ ENTER COLLAPSE / DEGRADE MODE."
        )

        dyn: Dict[str, float] = {}

        g_w = self._base.get(self.guardian_name, 0.0)
        l_w = self._base.get(self.liquidity_name, 0.0)

        if g_w <= 0 and l_w <= 0:
            # 连 guardian / liquidity 都没有 → 全部关灯
            for k in self._base.keys():
                dyn[k] = 0.0
            commentary = "Collapse: no guardian/liquidity leg available; full risk-off."
        else:
            # 只保留 guardian + liquidity，两腿内部归一化
            total_gl = max(g_w, 0.0) + max(l_w, 0.0)
            guardian_share = (g_w / total_gl) if g_w > 0 else 0.0
            liquidity_share = (l_w / total_gl) if l_w > 0 else 0.0

            for k in self._base.keys():
                if k == self.guardian_name:
                    dyn[k] = guardian_share
                elif k == self.liquidity_name:
                    dyn[k] = liquidity_share
                else:
                    dyn[k] = 0.0

            commentary = (
                "Collapse: routing collapsed onto guardian + liquidity only."
            )

        self._state.dynamic_weights = dyn
        self._state.degrade_mode = True
        self._state.commentary = commentary

    # ==============================================================

    def _renormalize_active(self, load: float):
        """
        在没有拉垮的前提下，对 active legs 做归一化。

        说明：
        - 使用 base_weight * multiplier 作为“未归一化权重”
        - 再除以总和 load，使 sum=1
        """
        if load <= 0:
            # 此时不算 collapse，但也没有有效腿了，直接视为软降级
            self._state.dynamic_weights = {k: 0.0 for k in self._base.keys()}
            self._state.degrade_mode = True
            self._state.commentary = "No active weight left; soft degrade."
            self.logger("[Router] No active legs after reallocation → soft degrade.")
            return

        dyn: Dict[str, float] = {}
        for k, base_w in self._base.items():
            if k in self._state.excluded_personas:
                dyn[k] = 0.0
            else:
                dyn[k] = (base_w * self._state.multipliers[k]) / load

        self._state.dynamic_weights = dyn
        self._state.degrade_mode = False
        self._state.commentary = "Reallocation with ramped multipliers."

        self.logger(f"[Router] New dynamic_weights={dyn}")

    # ==============================================================

    def get_weights(self) -> Dict[str, float]:
        """
        给 Alpha / 其他 personas 每个 tick 读取当前权重。
        """
        return dict(self._state.dynamic_weights)

    def in_degrade_mode(self) -> bool:
        return self._state.degrade_mode

    def commentary(self) -> str:
        return self._state.commentary

    def reset_tick(self):
        """
        每个市场 tick 结束（比如一个 bar 或一个决策周期）以后，
        可以调用 reset_tick 恢复 multipliers 和权重到 base 状态。
        """
        multipliers = {k: 1.0 for k in self._base.keys()}
        self._state = RouterState(
            dynamic_weights=dict(self._base),
            multipliers=multipliers,
            excluded_personas=set(),
            degrade_mode=False,
            commentary="Reset to base after tick.",
        )
        self.logger("[Router] Tick reset → back to base weights.")


