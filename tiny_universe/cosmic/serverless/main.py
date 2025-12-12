
# cosmic/serverless/main.py

from fastapi import FastAPI
from pydantic import BaseModel

# 将来你想接 tiny_universe 里的 engine / router，再从这里 import：
# from tiny_universe.toy_service import TinyUniverseService

class MarketSnapshot(BaseModel):
    symbol: str
    price: float

class Decision(BaseModel):
    symbol: str
    action: str
    size: float


app = FastAPI(
    title="Tiny Universe Lambda API",
    version="1.0.0",
    description="Cosmic TinyUniverse API running on AWS Lambda"
)


@app.get("/health")
def health():
    return {"status": "ok", "source": "cosmic/serverless/main.py"}


@app.post("/decide", response_model=Decision)
def decide(snapshot: MarketSnapshot):
    # TODO: 这里以后接你的 engine_full / toy_router / wormhole / quantum_bridge
    action = "BUY" if snapshot.price < 100 else "SELL"
    return Decision(symbol=snapshot.symbol, action=action, size=1.0)
