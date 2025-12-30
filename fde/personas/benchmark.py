
# personas/benchmark.py
from typing import Dict
from .base import BasePersona, MarketState

class BenchmarkPersona(BasePersona):
    name = "benchmark"

    def __init__(self, benchmark_weights: Dict[str, float]):
        self.benchmark_weights = benchmark_weights

    def act(self, state: MarketState) -> Dict[str, float]:
        # Provides a static benchmark portfolio
        return self.benchmark_weights
