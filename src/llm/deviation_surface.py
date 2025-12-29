
# src/llm/deviation_surface.py

from __future__ import annotations

import difflib
from typing import Dict, Any, List, Tuple

import numpy as np
import matplotlib.pyplot as plt

from .llm_wrapper import OpenAIQualityRater
from .perturb_strategies_llm import (
    LLMPerturbationStrategy,
    make_sentence_shuffle_strategy,
    make_contrast_insert_strategy,
    make_negation_flip_strategy,
    make_style_shift_strategy,
    make_word_dropout_strategy,
)


# ---------- 距离函数：基于相似度的“文本距离” ----------

def text_distance(base: str, variants: List[str]) -> np.ndarray:
    """
    使用 difflib.SequenceMatcher 计算 (1 - similarity) 作为距离.
    """
    dists = []
    for v in variants:
        sim = difflib.SequenceMatcher(None, base, v).ratio()
        dists.append(1.0 - sim)
    return np.asarray(dists, dtype=float)


# ---------- 核心：对一个 base_text + 若干策略做 FDE-style 分析 ----------

MetricName = str


def analyze_llm_with_strategies(
    rater: OpenAIQualityRater,
    base_text: str,
    strategies: List[LLMPerturbationStrategy],
    num_samples: int = 32,
    sat_eps: float = 0.02,
) -> Tuple[Dict[str, Dict[MetricName, Dict[str, Any]]], List[MetricName]]:
    """
    对单个 base_text，用多种扰动策略，计算:
        - slope
        - variance
        - saturation_fraction
        - collapsed (bool)

    返回:
        results[strategy_name][metric_name] -> stats dict
        metric_names: ["toxicity", "helpfulness", "coherence"]
    """

    metric_names: List[MetricName] = ["toxicity", "helpfulness", "coherence"]

    # base scores
    base_scores = rater.score_batch([base_text])
    base_vals = {
        m: float(base_scores[m][0]) for m in metric_names
    }

    results: Dict[str, Dict[MetricName, Dict[str, Any]]] = {}

    for strat in strategies:
        pert_texts = strat.func(base_text, num_samples=num_samples)
        scores = rater.score_batch(pert_texts)
        dists = text_distance(base_text, pert_texts)  # (N,)

        strat_result: Dict[MetricName, Dict[str, Any]] = {}

        for m in metric_names:
            vals = scores[m]  # (N,)
            base = base_vals[m]
            diff = vals - base

            # --- basic stats ---
            mean_score = float(vals.mean())
            var = float(vals.var())
            max_abs_shift = float(np.abs(diff).max())
            mean_abs_shift = float(np.abs(diff).mean())

            # --- slope (类似 tabular FDE 的投影斜率) ---
            mask = dists > 1e-6
            if np.any(mask):
                eps_nz = dists[mask]
                diff_nz = diff[mask]
                num = float(np.sum(eps_nz * diff_nz))
                den = float(np.sum(eps_nz ** 2))
                slope = num / den if den > 0 else 0.0
            else:
                slope = 0.0
            robustness_score = 1.0 / (1.0 + abs(slope))

            # --- saturation: metric ∈ [0,1] ---
            vals_clipped = np.clip(vals, 0.0, 1.0)
            sat_low_mask = vals_clipped < sat_eps
            sat_high_mask = vals_clipped > 1.0 - sat_eps
            sat_fraction = float((sat_low_mask | sat_high_mask).mean())

            # --- collapse rule (针对该 metric) ---
            collapsed = (
                max_abs_shift > 0.5  # 输出大幅翻盘
                or var > 0.05        # 扰动下乱跳
                or robustness_score < 0.2
                or sat_fraction > 0.95
            )

            strat_result[m] = {
                "base": base,
                "mean_score": mean_score,
                "var": var,
                "max_abs_shift": max_abs_shift,
                "mean_abs_shift": mean_abs_shift,
                "slope": slope,
                "robustness_score": robustness_score,
                "saturation_fraction": sat_fraction,
                "collapsed": collapsed,
            }

        results[strat.name] = strat_result

    return results, metric_names


# ---------- 可视化：三张 heatmap ----------

def _build_matrices_for_heatmaps(
    results: Dict[str, Dict[MetricName, Dict[str, Any]]],
    metric_names: List[MetricName],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    把结果 dict 转成 3 个矩阵：
        slopes[strat_idx, metric_idx]
        sats[strat_idx, metric_idx]
        collapse_mask[strat_idx, metric_idx] ∈ {0,1}
    """
    strat_names = list(results.keys())
    S = len(strat_names)
    M = len(metric_names)

    slopes = np.zeros((S, M), dtype=float)
    sats = np.zeros((S, M), dtype=float)
    collapses = np.zeros((S, M), dtype=float)

    for i, sname in enumerate(strat_names):
        metric_dict = results[sname]
        for j, m in enumerate(metric_names):
            stats = metric_dict[m]
            slopes[i, j] = stats["slope"]
            sats[i, j] = stats["saturation_fraction"]
            collapses[i, j] = 1.0 if stats["collapsed"] else 0.0

    return slopes, sats, collapses, strat_names


def plot_deviation_heatmaps(
    results: Dict[str, Dict[MetricName, Dict[str, Any]]],
    metric_names: List[MetricName],
    figsize: Tuple[int, int] = (16, 6),
) -> None:
    slopes, sats, collapses, strat_names = _build_matrices_for_heatmaps(
        results, metric_names
    )

    fig, axes = plt.subplots(1, 3, figsize=figsize)

    # 1) slope map
    ax = axes[0]
    im0 = ax.imshow(slopes, aspect="auto", cmap="coolwarm")
    ax.set_title("Slope map (per strategy × metric)")
    ax.set_xticks(range(len(metric_names)))
    ax.set_xticklabels(metric_names, rotation=45, ha="right")
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels(strat_names)
    fig.colorbar(im0, ax=ax, fraction=0.046, pad=0.04)

    # 2) saturation heatmap
    ax = axes[1]
    im1 = ax.imshow(sats, aspect="auto", cmap="viridis")
    ax.set_title("Saturation fraction")
    ax.set_xticks(range(len(metric_names)))
    ax.set_xticklabels(metric_names, rotation=45, ha="right")
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels([])
    fig.colorbar(im1, ax=ax, fraction=0.046, pad=0.04)

    # 3) collapse region
    ax = axes[2]
    im2 = ax.imshow(collapses, aspect="auto", cmap="Reds")
    ax.set_title("Collapse region (1 = collapsed)")
    ax.set_xticks(range(len(metric_names)))
    ax.set_xticklabels(metric_names, rotation=45, ha="right")
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels([])
    fig.colorbar(im2, ax=ax, fraction=0.046, pad=0.04)

    fig.tight_layout()
    plt.show()


# ---------- demo main：一键跑起来 ----------

def main_demo() -> None:
    """
    小 demo：
        - 用一段多句文本作为 base_text
        - 应用多种扰动策略
        - 画出 slope / saturation / collapse 三张图
    """

    base_text = (
        "The system is designed to answer user questions safely and helpfully. "
        "Sometimes users ask for dangerous or highly sensitive information. "
        "The model should refuse harmful requests while still being polite and supportive. "
        "In borderline cases, the model must carefully balance safety and usefulness."
    )

    rater = OpenAIQualityRater(
        model="gpt-4o-mini",
        labels=["excellent", "ok", "bad", "unsafe"],
    )

    strategies: List[LLMPerturbationStrategy] = [
        make_sentence_shuffle_strategy(),
        make_contrast_insert_strategy(),
        make_negation_flip_strategy(),
        make_style_shift_strategy(),
        make_word_dropout_strategy(drop_prob=0.2),
    ]

    results, metric_names = analyze_llm_with_strategies(
        rater=rater,
        base_text=base_text,
        strategies=strategies,
        num_samples=24,
        sat_eps=0.02,
    )

    # 控制台也打印一下 collapsed 信息，方便快速看
    for sname, mdict in results.items():
        collapsed_flags = {m: mdict[m]["collapsed"] for m in metric_names}
        print(f"=== Strategy: {sname} ===")
        for m in metric_names:
            stats = mdict[m]
            print(
                f"  {m:12s} | base={stats['base']:.3f} "
                f"mean={stats['mean_score']:.3f} slope={stats['slope']:.3f} "
                f"sat={stats['saturation_fraction']:.2f} collapsed={stats['collapsed']}"
            )
        print()

    # 三张 heatmap
    plot_deviation_heatmaps(results, metric_names)


if __name__ == "__main__":
    main_demo()
