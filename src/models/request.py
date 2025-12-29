# src/models/request.py

from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field


class ExplainMeta(BaseModel):
    """
    附加信息：
    - user_question: 用户问的自然语言问题
    - language: 返回解释语言 (en / zh-CN / zh / ...)
    - extra: 其他你想透传的东西（trace_id、user_id等）
    """
    user_question: str = Field(
        default="",
        description="Natural language question from the end user.",
    )
    language: str = Field(
        default="en",
        description="Language of the explanation (e.g. 'en', 'zh-CN').",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra metadata.",
    )


class ExplainRequest(BaseModel):
    """
    后端 /explain API 的请求体。

    x0:
        - 单样本特征向量
        - 你可以约定是 1D (List[float])，或 2D (List[List[float]]) 再在后端自己转成 np.array。
    meta:
        - 附加信息（上面的 ExplainMeta）
    """

    x0: Union[List[float], List[List[float]]] = Field(
        ...,
        description="Feature vector of the instance to be explained.",
    )
    meta: ExplainMeta = Field(
        default_factory=ExplainMeta,
        description="Additional metadata for the explanation request.",
    )
