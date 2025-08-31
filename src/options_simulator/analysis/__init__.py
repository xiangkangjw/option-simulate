"""
Analysis module for advanced options hedging strategies.

This module provides sophisticated analysis capabilities for tail hedging strategies,
including volatility regime analysis, exit strategy management, and jump-diffusion pricing.
"""

from .volatility_regime import VolatilityRegimeAnalyzer
from .exit_strategy import ExitStrategyManager
from .hedge_comparison import HedgeComparisonEngine, HedgingStrategy

__all__ = [
    "VolatilityRegimeAnalyzer",
    "ExitStrategyManager", 
    "HedgeComparisonEngine",
    "HedgingStrategy",
]