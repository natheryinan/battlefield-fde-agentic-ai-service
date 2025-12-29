"""
background.py

专门负责 FDE 所需的背景样本：
- 从训练集里截取 / 采样一部分
- 保存到 artifacts/data/background.npy
- 提供加载和简单自检工具
"""

from __future__ import annotations
import numpy as np
from pathlib import Path
from typing import Union

# 统一路径
ARTIFACTS_DATA_DIR = Path("artifacts") / "data"
BACKGROUND_PATH = ARTIFACTS_DATA_DIR / "background.npy"


def save_background(
    X: np.ndarray,
    n_samples: int = 1000,
    path: Union[str, Path] = BACKGROUND_PATH,
    shuffle: bool = True,
) -> Path:
    """
    从训练集 X 中选一部分作为 FDE 背景，并保存为 .npy

    X: 训练特征，shape = (N, d)
    n_samples: 采样多少条作为 background
    path: 保存路径
    shuffle: 是否先打乱再取前 n_samples
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(X, np.ndarray):
        X = np.asarray(X)

    # 限制 n_samples 不要超过数据本身
    n = min(n_samples, X.shape[0])

    if shuffle:
        idx = np.random.permutation(X.shape[0])[:n]
        bg = X[idx]
    else:
        bg = X[:n]

    np.save(path, bg)
    print(f"[background.py] Saved background: shape={bg.shape}, path={path}")
    return path


def load_background(path: Union[str, Path] = BACKGROUND_PATH) -> np.ndarray:
    """
    读取背景样本 background.npy
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"[background.py] Background file not found: {path}.\n"
            f"请先用 save_background() 生成。"
        )

    bg = np.load(path)
    print(f"[background.py] Loaded background: shape={bg.shape}, path={path}")
    return bg


def ensure_background(
    X: np.ndarray,
    n_samples: int = 1000,
    path: Union[str, Path] = BACKGROUND_PATH,
) -> np.ndarray:
    """
    如果 background.npy 不存在，则基于 X 生成；
    否则直接读取并返回。

    用在训练脚本里很方便。
    """
    path = Path(path)
    if path.exists():
        return load_background(path)
    save_background(X, n_samples=n_samples, path=path)
    return load_background(path)


if __name__ == "__main__":
    # 小自检：如果已经有 background.npy，就打印一下 shape
    try:
        bg = load_background()
        print("[background.py] Background preview (first row):")
        print(bg[0])
    except FileNotFoundError as e:
        print(e)
