from __future__ import annotations
from typing import Callable, Any, Dict
from utils.api.fde_engine import FDEEngine

class LLMEngine:
    """
    负责：
    - 理解用户问题
    - 决定要不要调用 FDEEngine / SHAP / 日志查询
    - 整合结构化结果 → 解释 / 报告
    """
    def __init__(self, llm_client, fde_engine: FDEEngine):
        self.llm = llm_client
        self.fde = fde_engine

    def explain_instance(self, x0, meta: dict) -> str:
        # 1. 用 FDE 做数值分析
        fde_result = self.fde.analyze(x0)

        # 2. 把 fde_result + meta 喂给 LLM 让它写解释
        prompt = self._build_prompt(fde_result, meta)
        explanation = self.llm.generate(prompt)

        return explanation
