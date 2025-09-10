"""Service Factory for dependency injection and service management."""

from typing import Optional
import logging

from .market_data_service import MarketDataService
from ..config import settings

logger = logging.getLogger(__name__)


class ServiceFactory:
    """Factory for creating and managing service instances."""
    
    _market_data_service: Optional[MarketDataService] = None
    
    @classmethod
    def get_market_data_service(cls, 
                               primary_provider: Optional[str] = None,
                               fallback_provider: Optional[str] = None,
                               enable_caching: bool = True,
                               force_new: bool = False) -> MarketDataService:
        """Get or create a MarketDataService instance.
        
        Args:
            primary_provider: Primary data provider ('yahoo' or 'alphavantage')
            fallback_provider: Fallback data provider
            enable_caching: Whether to enable caching
            force_new: Force creation of a new instance
            
        Returns:
            MarketDataService instance
        """
        if cls._market_data_service is None or force_new:
            # Determine providers based on configuration
            if primary_provider is None:
                if settings.alpha_vantage_api_key:
                    primary_provider = "alphavantage"
                else:
                    primary_provider = "yahoo"
            
            if fallback_provider is None:
                fallback_provider = "yahoo"  # Yahoo as reliable fallback
            
            logger.info(f"Creating MarketDataService: {primary_provider} -> {fallback_provider}")
            
            cls._market_data_service = MarketDataService(
                primary_provider=primary_provider,
                fallback_provider=fallback_provider,
                enable_caching=enable_caching
            )
        
        return cls._market_data_service
    
    @classmethod
    def reset_services(cls) -> None:
        """Reset all service instances (useful for testing)."""
        cls._market_data_service = None
        logger.info("Reset all service instances")
    
    @classmethod
    def configure_for_testing(cls, use_mock_data: bool = True) -> MarketDataService:
        """Configure services for testing environment.
        
        Args:
            use_mock_data: Whether to use mock data providers
            
        Returns:
            Configured MarketDataService for testing
        """
        if use_mock_data:
            # For testing, we can still use real providers but with overrides
            # The service layer handles fallback gracefully
            provider = "yahoo"  # Use Yahoo as it doesn't require API keys
        else:
            provider = "yahoo"
        
        cls._market_data_service = MarketDataService(
            primary_provider=provider,
            fallback_provider=provider,
            enable_caching=False  # Disable caching for tests
        )
        
        logger.info("Configured services for testing")
        return cls._market_data_service
    
    @classmethod
    def get_provider_status(cls) -> dict:
        """Get status information about configured providers.
        
        Returns:
            Dictionary with provider status information
        """
        service = cls.get_market_data_service()
        
        status = {
            'primary_provider': type(service.manager.primary).__name__,
            'fallback_provider': type(service.manager.fallback).__name__,
            'caching_enabled': service.cache is not None,
            'service_healthy': service.is_healthy(),
            'has_alpha_vantage_key': bool(settings.alpha_vantage_api_key)
        }
        
        return status