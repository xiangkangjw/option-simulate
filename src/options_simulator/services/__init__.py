"""Service layer for options simulator.

This module provides clean separation between CLI and business logic,
with dependency injection for testability.
"""

from .market_data_service import MarketDataService
from .service_factory import ServiceFactory

__all__ = ['MarketDataService', 'ServiceFactory']