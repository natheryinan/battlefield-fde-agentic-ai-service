import numpy as np
import pandas as pd

from dataclasses import dataclass
from typing import Callable, Dict, Any, List

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import RandomForestClassifier
from src.utils.api.fde_engine import FDEEngine, PerturbationStrategy





# ============================================================
# 2. Toy Demo 的扰动策略（包括 无限 OOD）
# ============================================================

def make_plasticity_gaussian_strategy(scale: float = 0.1, name: str = None) -> PerturbationStrategy:
    """
    可塑性扰动：
    - 小幅高斯噪声，测试模型在局部附近的平滑性 / 连续性
    x' = x0 + N(0, scale * std_bg)
    """
    def _func(x0: np.ndarray, X_bg: np.ndarray, num_samples: int) -> np.ndarray:
        x0 = x0.reshape(-1)
        X_bg = np.asarray(X_bg)
        std = X_bg.std(axis=0) + 1e-8
        d = x0.shape[0]
        noise = np.random.normal(scale=std * scale, size=(num_samples, d))
        return x0 + noise

    if name is None:
        name = f"plasticity_gaussian(scale={scale})"
    return PerturbationStrategy(name=name, func=_func)


def make_masking_strategy(drop_prob: float = 0.3, name: str = None) -> PerturbationStrategy:
    """
    遮蔽数据：
    - 随机遮掉部分特征，用背景均值填充
    - 测试模型对缺失 / 隐藏信息的鲁棒性
    """
    def _func(x0: np.ndarray, X_bg: np.ndarray, num_samples: int) -> np.ndarray:
        x0 = x0.reshape(-1)
        X_bg = np.asarray(X_bg)
        bg_mean = X_bg.mean(axis=0)

        d = x0.shape[0]
        X = np.repeat(x0.reshape(1, -1), num_samples, axis=0)

        # 1=保留原值，0=遮蔽
        mask = (np.random.rand(num_samples, d) > drop_prob).astype(float)
        X_masked = mask * X + (1 - mask) * bg_mean
        return X_masked

    if name is None:
        name = f"masking(drop_prob={drop_prob})"
    return PerturbationStrategy(name=name, func=_func)


def make_infinite_ood_strategy(
    min_exp: int = 3,
    max_exp: int = 15,
    name: str = None
) -> PerturbationStrategy:
    """
    Asymptotic Infinity OOD Stress:
        x_inf = μ + α * σ * direction
        α = 10^k, k ∈ [min_exp, max_exp]
    用指数级爆炸把点推到“近似无限”的分布外区域。
    """
    def _func(x0: np.ndarray, X_bg: np.ndarray, num_samples: int) -> np.ndarray:
        X_bg = np.asarray(X_bg)
        μ = X_bg.mean(axis=0)
        σ = X_bg.std(axis=0) + 1e-8
        d = μ.shape[0]

        # 随机方向
        direction = np.random.choice([-1.0, 1.0], size=(num_samples, d))
        # 指数级爆炸因子 10^k
        exponents = np.random.uniform(min_exp, max_exp, size=(num_samples, 1))
        α = np.power(10.0, exponents)

        X_inf = μ + direction * α * σ
        # 防止 inf / nan
        X_inf = np.nan_to_num(X_inf, nan=0.0, posinf=1e308, neginf=-1e308)
        return X_inf

    if name is None:
        name = f"infinite_OOD(10^{min_exp}~10^{max_exp})"
    return PerturbationStrategy(name=name, func=_func)


# ============================================================
# 3. Toy Demo：构造信用风控数据 + 训练 RF 黑箱模型
# ============================================================

def build_toy_credit_model():
    """
    构造一个简单的信用风控 toy 数据集 + 训练 RF 模型
    返回：clf, X_train, X_test, y_train, y_test
    """
    rng = np.random.RandomState(42)
    n = 2000

    X_df = pd.DataFrame({
        "age": rng.randint(21, 70, size=n),
        "annual_income": rng.normal(55000, 15000, size=n),
        "credit_card_debt": rng.exponential(5000, size=n),
        "mortgage_balance": rng.exponential(80000, size=n),
        "num_late_payments": rng.poisson(1.5, size=n),
    })

    logit = (
        -5
        + 0.04 * (35 - X_df["age"])
        - 0.00003 * X_df["annual_income"]
        + 0.0002 * X_df["credit_card_debt"]
        + 0.00001 * X_df["mortgage_balance"]
        + 0.3 * X_df["num_late_payments"]
    )
    p_default = 1 / (1 + np.exp(-logit))
    y = (rng.rand(n) < p_default).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X_df.values, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    auc = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
    print(f"Toy credit RF Test AUC: {auc:.4f}")

    return clf, X_train, X_test, y_train, y_test


# ============================================================
# 4. main(): 实例化 FDE 引擎 + 注册策略 + 跑一条样本
# ============================================================

def main():
    # 1) 训练 toy RF 模型
    clf, X_train, X_test, y_train, y_test = build_toy_credit_model()

    # 2) 构造 FDE 引擎
    fde = FDEEngine(model=clf, X_background=X_train, class_index=1)

    # 3) 注册 Toy Demo 的三种扰动策略
    fde.add_strategy(make_plasticity_gaussian_strategy(scale=0.1))
    fde.add_strategy(make_masking_strategy(drop_prob=0.3))
    fde.add_strategy(make_infinite_ood_strategy(min_exp=3, max_exp=15))

    # 4) 选一个样本做极限 OOD + 其它策略分析
    x0 = X_test[0]  # 任意一条样本
    results = fde.analyze_point(x0, num_samples=2000)

    # 5) 打印每个策略的指标
    for name, stats in results.items():
        print(f"\n=== Strategy: {name} ===")
        for k, v in stats.items():
            if k == "scores":
                continue
            print(f"{k:25s}: {v}")


if __name__ == "__main__":
    main()
