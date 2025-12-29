# src/engine/explanation_builder.py

from typing import Any, Dict, List, Tuple


class ExplanationBuilder:
    """
    负责把 FDE 的数值结果，变成 LLM 可以吃的 prompt 片段 / 文本描述。

    用法示例（在 LLMEngine 里）：
        builder = ExplanationBuilder()
        prompt = builder.build_prompt(user_question, fde_result, meta)
    """

    def build_prompt(
        self,
        user_question: str,
        fde_result: Dict[str, Any],
        meta: Dict[str, Any] | None = None,
    ) -> str:
        """
        把用户问题 + FDE 数值结果 → 拼成一个完整的 LLM prompt。
        """
        meta = meta or {}
        language = meta.get("language", "en")

        summary_block = self._summarize_fde(fde_result, language=language)

        prompt = f"""
You are an AI assistant that explains model decisions for end users.

User question:
{user_question}

Model analysis (FDE results):
{summary_block}

Please explain in {language}:
- Why the model behaves this way for this instance.
- Which features had the biggest positive / negative impact.
- Any caveats or limitations the user should know.
Use clear, non-technical language.
"""
        return prompt.strip()

    # --------------------------------------------------------------------- #
    #  内部辅助函数：从 fde_result 中抽取“top features”等关键信息
    # --------------------------------------------------------------------- #

    def _summarize_fde(
        self,
        fde_result: Dict[str, Any],
        language: str = "en",
        top_k: int = 5,
    ) -> str:
        """
        根据你自己的 FDEEngine 返回的结构，自行适配：

        这里假设 fde_result 里可能有这些字段：
            - "feature_names": List[str]
            - "importance": List[float] 或 Dict[str, float]
        如果没有，就做个尽量通用的 fallback。
        """
        feature_names: List[str] | None = None
        importance: Dict[str, float] | None = None

        # 1) 尝试从常见结构里抽取
        if "feature_names" in fde_result and "importance" in fde_result:
            feature_names = fde_result["feature_names"]
            raw_importance = fde_result["importance"]

            if isinstance(raw_importance, dict):
                importance = dict(raw_importance)
            elif isinstance(raw_importance, list) and feature_names:
                # list 对应 feature_names
                importance = {
                    fname: float(score)
                    for fname, score in zip(feature_names, raw_importance)
                }

        # 2) 如果上面不成立，fallback 把所有数值字段都列一列
        if importance is None:
            return self._generic_dump(fde_result)

        # 3) 选 top-k
        items: List[Tuple[str, float]] = sorted(
            importance.items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )[:top_k]

        if language.startswith("zh"):
            header = "前几大驱动特征（按影响绝对值排序）:\n"
            lines = [
                f"- 特征 `{name}` 的影响分数: {score:.4f}"
                for name, score in items
            ]
        else:
            header = "Top driving features (sorted by absolute impact):\n"
            lines = [
                f"- Feature `{name}` impact score: {score:.4f}"
                for name, score in items
            ]

        return header + "\n".join(lines)

    def _generic_dump(self, fde_result: Dict[str, Any]) -> str:
        """
        当你还没定义好 fde_result schema 时，用一个通用 dump。
        """
        lines: List[str] = []
        for k, v in fde_result.items():
            # 避免太长：只展示前 200 字符
            text = str(v)
            if len(text) > 200:
                text = text[:200] + " ...[truncated]"
            lines.append(f"- {k}: {text}")
        return "Raw FDE result snapshot:\n" + "\n".join(lines)
