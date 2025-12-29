# src/llm/perturb_strategies_llm.py

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable, List


@dataclass
class LLMPerturbationStrategy:
    """
    LLM 文本扰动策略：
        func(base_text: str, num_samples: int) -> List[str]
    """
    name: str
    func: Callable[[str, int], List[str]]


# ---------- 工具函数 ----------

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")


def _split_sentences(text: str) -> List[str]:
    sents = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    return sents or [text]


def _join_sentences(sents: List[str]) -> str:
    return " ".join(sents)


# ---------- 具体策略 ----------

def make_sentence_shuffle_strategy(name: str = "sentence_shuffle") -> LLMPerturbationStrategy:
    """
    句子级洗牌：对多句文本随机打乱顺序。
    """

    def _func(base: str, num_samples: int) -> List[str]:
        sents = _split_sentences(base)
        out: List[str] = []
        for _ in range(num_samples):
            s = sents[:]  # copy
            random.shuffle(s)
            out.append(_join_sentences(s))
        return out

    return LLMPerturbationStrategy(name=name, func=_func)


def make_contrast_insert_strategy(name: str = "contrast_insert") -> LLMPerturbationStrategy:
    """
    在文本中插入对比/反例句子，增强“立场对比”。
    """

    CONTRAST_TEMPLATES = [
        "However, some people take the opposite view and argue the reverse.",
        "On the other hand, critics strongly disagree with this perspective.",
        "In contrast, there are reports suggesting the outcome can be very different.",
        "Nevertheless, there are serious concerns about the safety and fairness of this.",
    ]

    def _func(base: str, num_samples: int) -> List[str]:
        sents = _split_sentences(base)
        out: List[str] = []
        for _ in range(num_samples):
            s = sents[:]
            insert_pos = random.randint(0, len(s))
            contrast_sent = random.choice(CONTRAST_TEMPLATES)
            s.insert(insert_pos, contrast_sent)
            out.append(_join_sentences(s))
        return out

    return LLMPerturbationStrategy(name=name, func=_func)


def make_negation_flip_strategy(name: str = "negation_flip") -> LLMPerturbationStrategy:
    """
    粗暴“否定翻转”：对部分句子加 not / remove not。
    只是 heuristic，目的是制造语义翻转扰动。
    """

    def _flip_sent(sent: str) -> str:
        # 非严格 NLP，只做非常粗糙的替换
        if " not " in sent:
            return sent.replace(" not ", " ")
        if " no " in sent:
            return sent.replace(" no ", " ")
        # 如果没有否定词，就加一个
        return sent.replace(" is ", " is not ").replace(" are ", " are not ")

    def _func(base: str, num_samples: int) -> List[str]:
        sents = _split_sentences(base)
        out: List[str] = []
        for _ in range(num_samples):
            s = sents[:]
            k = max(1, len(s) // 3)  # 翻转约 1/3 句子
            idxs = random.sample(range(len(s)), k=min(k, len(s)))
            for idx in idxs:
                s[idx] = _flip_sent(s[idx])
            out.append(_join_sentences(s))
        return out

    return LLMPerturbationStrategy(name=name, func=_func)


def make_style_shift_strategy(name: str = "style_shift") -> LLMPerturbationStrategy:
    """
    风格扰动：在头尾增加“学术 / 口语 / 命令式”说明，改变整体语境。
    """

    PREFIXES = [
        "From an academic and highly cautious perspective, ",
        "Speaking casually as a friend: ",
        "From a strict legal and compliance viewpoint, ",
        "As an emotionally neutral observer, ",
    ]
    SUFFIXES = [
        " Please explain this in a neutral and balanced way.",
        " Focus on potential harms and ethical risks.",
        " Emphasize practical, step-by-step guidance.",
        " Highlight emotional impact and long-term consequences.",
    ]

    def _func(base: str, num_samples: int) -> List[str]:
        out: List[str] = []
        for _ in range(num_samples):
            p = random.choice(PREFIXES)
            s = random.choice(SUFFIXES)
            out.append(p + base + " " + s)
        return out

    return LLMPerturbationStrategy(name=name, func=_func)


def make_word_dropout_strategy(
    drop_prob: float = 0.15,
    name: str = "word_dropout",
) -> LLMPerturbationStrategy:
    """
    词级 dropout：随机删掉部分 token，模拟“噪声 / 缺失信息”。
    """

    def _func(base: str, num_samples: int) -> List[str]:
        tokens = base.split()
        n = len(tokens)
        out: List[str] = []
        for _ in range(num_samples):
            kept = [
                tok for tok in tokens if random.random() > drop_prob or n <= 3
            ]
            if not kept:
                kept = tokens[: max(1, n // 4)]
            out.append(" ".join(kept))
        return out

    return LLMPerturbationStrategy(name=name, func=_func)
