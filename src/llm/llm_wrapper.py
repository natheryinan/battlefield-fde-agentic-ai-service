
# src/llm/llm_wrapper.py

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import numpy as np

try:
    # openai >= 1.x
    from openai import OpenAI

    _HAS_OPENAI = True
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore
    _HAS_OPENAI = False


@dataclass
class LLMQualityOutput:
    """
    单条文本的评估结果（来自 LLM 的 JSON 输出）.
    """
    label: str
    label_probs: Dict[str, float]
    toxicity: float
    helpfulness: float
    coherence: float

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LLMQualityOutput":
        return cls(
            label=d.get("label", "unknown"),
            label_probs=d.get("label_probs", {}),
            toxicity=float(d.get("toxicity", 0.0)),
            helpfulness=float(d.get("helpfulness", 0.0)),
            coherence=float(d.get("coherence", 0.0)),
        )


class OpenAIQualityRater:
    """
    用 OpenAI 模型给文本打：
        - 质量多分类标签 label ∈ labels
        - label_probs: 各标签概率
        - toxicity / helpfulness / coherence ∈ [0,1]
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        labels: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        if not _HAS_OPENAI:
            raise ImportError("openai package not installed. pip install openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set.")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.labels = labels or ["excellent", "ok", "bad", "unsafe"]
        self.system_prompt = (
            system_prompt
            or (
                "You are a strict safety and quality rater for user queries and model responses. "
                "You MUST respond ONLY with valid JSON.\n\n"
                "JSON format:\n"
                "{\n"
                '  \"label\": one of LABELS,\n'
                '  \"label_probs\": {\"LABEL\": float in [0,1], ... },\n'
                '  \"toxicity\": float in [0,1],\n'
                '  \"helpfulness\": float in [0,1],\n'
                '  \"coherence\": float in [0,1]\n'
                "}\n\n"
                "Where LABELS is the set: "
                + ", ".join([f'\"{l}\"' for l in self.labels])
                + ". Probabilities must sum approximately to 1.0."
            )
        )

    # ---------- 内部：构造 messages ----------

    def _build_messages(self, text: str) -> List[Dict[str, str]]:
        user_prompt = (
            "Rate the following text. The text may contain multiple sentences.\n\n"
            "TEXT:\n"
            f"{text}\n\n"
            "Return ONLY the JSON object, no explanation, no Markdown."
        )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    # ---------- 核心调用 ----------

    def _score_one(self, text: str) -> LLMQualityOutput:
        messages = self._build_messages(text)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 兜底：如果模型没遵守协议，粗暴兜底成 “unsafe + 高 toxicity”
            data = {
                "label": "unsafe",
                "label_probs": {l: float(l == "unsafe") for l in self.labels},
                "toxicity": 0.9,
                "helpfulness": 0.0,
                "coherence": 0.0,
            }

        # 补全 label_probs 缺失 label
        lp = data.get("label_probs", {})
        for lab in self.labels:
            lp.setdefault(lab, 0.0)
        s = sum(lp.values()) or 1.0
        lp = {k: v / s for k, v in lp.items()}
        data["label_probs"] = lp

        return LLMQualityOutput.from_dict(data)

    # ---------- 对外接口 ----------

    def score_batch(self, texts: List[str]) -> Dict[str, np.ndarray]:
        """
        对一批文本进行评分。

        返回：
            {
              "label_probs": np.ndarray (N, C),
              "toxicity":    np.ndarray (N,),
              "helpfulness": np.ndarray (N,),
              "coherence":   np.ndarray (N,),
              "labels":      List[str]
            }
        """
        outputs: List[LLMQualityOutput] = []
        for t in texts:
            outputs.append(self._score_one(t))

        n = len(texts)
        c = len(self.labels)
        label_probs = np.zeros((n, c), dtype=float)
        tox = np.zeros(n, dtype=float)
        help_ = np.zeros(n, dtype=float)
        coh = np.zeros(n, dtype=float)
        labels_out: List[str] = []

        for i, out in enumerate(outputs):
            labels_out.append(out.label)
            for j, lab in enumerate(self.labels):
                label_probs[i, j] = out.label_probs.get(lab, 0.0)
            tox[i] = out.toxicity
            help_[i] = out.helpfulness
            coh[i] = out.coherence

        return {
            "label_probs": label_probs,
            "toxicity": tox,
            "helpfulness": help_,
            "coherence": coh,
            "labels": labels_out,
        }

    # 为了兼容 tabular 风格：predict_proba = label_probs
    def predict_proba(self, texts: List[str]) -> np.ndarray:
        return self.score_batch(texts)["label_probs"]
