
# src/utils/api/__init__.py
# mark src as a package

"""
API-level public exports for the FDE Engine.

External modules can import:
    from utils.api import FDEEngine, PerturbationStrategy
"""

from .fde_engine import FDEEngine, PerturbationStrategy

__all__ = [
    "FDEEngine",
    "PerturbationStrategy",
]
