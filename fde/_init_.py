"""
FDE - Feature Deviation Engine
AI-driven multi-persona financial decision engine.
"""

# ---- Expose major modules for easy import ----

from .interfaces.core import (
    MarketSnapshot,
    PortfolioState,
    PersonaContext,
    OptionSnapshot,
    RiskLimits,
)

from .factors.cross_section import CrossSectionFactors

from .personas.alpha_multi import MultiFactorAlphaPersona
from .personas.guardian import GuardianPersona
from .personas.convexity import ConvexityPersona

# ---- Metadata ----
__all__ = [
    "MarketSnapshot",
    "PortfolioState",
    "PersonaContext",
    "OptionSnapshot",
    "RiskLimits",
    "CrossSectionFactors",
    "MultiFactorAlphaPersona",
    "GuardianPersona",
    "ConvexityPersona",
]

__version__ = "0.1.0"
