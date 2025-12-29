import os
import sys

CURRENT_DIR = os.path.dirname(__file__)                # .../src/server
SRC_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # .../src
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

# artifacts 实际放在 src/artifacts 下
PROJECT_ROOT = SRC_ROOT

MODEL_PATH = os.path.join(PROJECT_ROOT, "artifacts", "model", "my_model.h5")
BACKGROUND_PATH = os.path.join(PROJECT_ROOT, "artifacts", "data", "background.npy")




from fastapi import FastAPI
from engine.blackbox_keras import KerasBlackBox         # src/engine/blackbox_keras.py
from utils.api.fde_engine import FDEEngine              # src/utils/api/fde_engine.py
from llm.llm_engine import LLMEngine              # src/engine/llm_engine.py

import numpy as np
from server.routers import explain



def create_llm_engine():
    model = KerasBlackBox(MODEL_PATH)
    background = np.load(BACKGROUND_PATH)

    llm_engine = LLMEngine(
        model=model,
        background=background,
    )
    return llm_engine


    



# --------------------------------------------------------------------------- #
# 2. FastAPI 应用工厂：在这里挂 app.state.llm_engine
# --------------------------------------------------------------------------- #


def create_app() -> FastAPI:
    """
    FastAPI 应用工厂。
    在这里把 llm_engine 挂到 app.state 上，供所有路由使用。
    """
    app = FastAPI(
        title="FDE + LLM Explainability API",
        version="0.2.0",
    )

    # 👇 核心：挂载 LLMEngine 到 app.state
    app.state.llm_engine = create_llm_engine()

    # 注册路由
    app.include_router(
        explain.router,
        prefix="/api",
        tags=["explain"],
    )

    return app



# FastAPI 要求的全局 app 对象
app = create_app()


# 方便直接 `python -m server.main` 跑起来
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
