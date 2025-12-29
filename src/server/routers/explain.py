# src/server/routers/explain.py

from fastapi import APIRouter, HTTPException, Request

from engine.llm_engine import LLMEngine
from models.request import ExplainRequest
from models.response import ExplainResponse

router = APIRouter()


@router.post("/explain")
async def explain(request: Request, body: ExplainRequest) -> dict:

    # 从 app.state 拿 llm_engine
    llm_engine: LLMEngine | None = getattr(request.app.state, "llm_engine", None)

    if llm_engine is None:
        raise HTTPException(
            status_code=500,
            detail="LLMEngine is not configured on app.state.llm_engine",
        )

    result = llm_engine.explain(
        x0=body.x0,
        meta=body.meta.model_dump(),
    )

    return result

