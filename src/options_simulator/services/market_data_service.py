"""Market Data Service for real-time and historical data access."""

import asyncio
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

from ..data.providers import MarketDataManager, DataProvider
from ..data.cache import HybridCache
from ..exceptions import (
    DataProviderError, APIRateLimitError, StaleDataError,
    DataValidationError, CircuitBreaker, handle_api_error, error_metrics
)
from ..config import settings

# Set up logging
logger = logging.getLogger(__name__)


class EnhancedMarketDataService:
    """Enhanced market data service with circuit breaker and error handling."""
    
    def __init__(self,
                 primary_provider: str = "yahoo",
                 fallback_provider: str = "yahoo", 
                 enable_caching: bool = True,
                 circuit_breaker_threshold: int = 5,
                 circuit_recovery_timeout: float = 300.0):
        """Initialize enhanced market data service.
        
        Args:
            primary_provider: Primary data provider
            fallback_provider: Fallback data provider
            enable_caching: Whether to enable caching
            circuit_breaker_threshold: Circuit breaker failure threshold
            circuit_recovery_timeout: Circuit breaker recovery timeout
        """
        self.manager = MarketDataManager(primary_provider, fallback_provider)
        self.cache = HybridCache() if enable_caching else None
        self.circuit_breaker = CircuitBreaker(circuit_breaker_threshold, circuit_recovery_timeout)
        
        logger.info(f"Initialized EnhancedMarketDataService: {primary_provider} -> {fallback_provider}")
        logger.info(f"Circuit breaker: {circuit_breaker_threshold} failures, {circuit_recovery_timeout}s recovery")
    
    def _handle_provider_error(self, error: Exception, provider: str, operation: str) -> None:
        """Handle and log provider errors with proper exception conversion."""
        converted_error = handle_api_error(error, provider)
        error_metrics.record_error(converted_error)
        
        logger.warning(f"Provider error in {operation}: {converted_error}")
        
        if isinstance(converted_error, APIRateLimitError):
            logger.info(f"Rate limit hit for {provider}, circuit breaker will manage retries")
        
        raise converted_error


class MarketDataService(EnhancedMarketDataService):
    """Service layer for market data operations with enhanced error handling."""
    
    def __init__(self, 
                 primary_provider: str = "yahoo", 
                 fallback_provider: str = "yahoo",
                 enable_caching: bool = True):
        """Initialize market data service.
        
        Args:
            primary_provider: Primary data provider ('yahoo' or 'alphavantage')
            fallback_provider: Fallback data provider
            enable_caching: Whether to enable caching
        """
        super().__init__(primary_provider, fallback_provider, enable_caching)
        self._last_error_time = 0
        self._error_count = 0
    
    def get_current_market_conditions(self, 
                                    symbol: str = "SPY",
                                    vix_override: Optional[float] = None,
                                    spy_override: Optional[float] = None) -> Dict[str, Any]:
        """Get comprehensive current market conditions with real data.
        
        Args:
            symbol: Primary equity symbol to analyze
            vix_override: Override VIX level for testing
            spy_override: Override SPY price for testing
            
        Returns:
            Dictionary with market conditions
        """
        cache_key = f"market_conditions_{symbol}_{vix_override}_{spy_override}"
        
        # Check cache first (5-minute TTL for real-time data)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Using cached market conditions for {symbol}")
                return cached
        
        try:
            logger.info(f"Fetching real-time market conditions for {symbol}")
            
            # Define data fetching functions for circuit breaker protection
            def fetch_spy_price():
                return self.manager.get_stock_price(symbol)
            
            def fetch_vix_level():
                return self.manager.get_vix_level()
            
            def fetch_treasury_rate():
                return self.manager.get_treasury_rate("10Y")
            
            # Use override values if provided, otherwise fetch real data with circuit breaker
            conditions = {}
            
            if spy_override is not None:
                conditions['spy_price'] = float(spy_override)
                logger.info(f"Using override SPY price: ${spy_override}")
            else:
                try:
                    conditions['spy_price'] = self.circuit_breaker.call(fetch_spy_price)
                    if conditions['spy_price'] == 0.0:
                        raise DataValidationError(
                            type(self.manager.primary).__name__,
                            'spy_price', 
                            0.0,
                            'positive price value'
                        )
                except Exception as e:
                    self._handle_provider_error(e, type(self.manager.primary).__name__, "fetch_spy_price")
                    conditions['spy_price'] = 420.0  # Fallback
                    logger.warning(f"Using fallback SPY price: $420.00")
            
            if vix_override is not None:
                conditions['vix'] = float(vix_override)
                logger.info(f"Using override VIX level: {vix_override}")
            else:
                try:
                    conditions['vix'] = self.circuit_breaker.call(fetch_vix_level)
                    if not (5 <= conditions['vix'] <= 100):
                        raise DataValidationError(
                            type(self.manager.primary).__name__,
                            'vix',
                            conditions['vix'], 
                            'VIX between 5 and 100'
                        )
                except Exception as e:
                    self._handle_provider_error(e, type(self.manager.primary).__name__, "fetch_vix_level")
                    conditions['vix'] = 20.0  # Fallback
                    logger.warning(f"Using fallback VIX level: 20.0")
            
            # Get risk-free rate with circuit breaker protection
            try:
                conditions['risk_free_rate'] = self.circuit_breaker.call(fetch_treasury_rate)
                if not (0 <= conditions['risk_free_rate'] <= 0.15):
                    raise DataValidationError(
                        type(self.manager.primary).__name__,
                        'risk_free_rate',
                        conditions['risk_free_rate'],
                        'rate between 0 and 15%'
                    )
            except Exception as e:
                self._handle_provider_error(e, type(self.manager.primary).__name__, "fetch_treasury_rate")
                conditions['risk_free_rate'] = 0.045  # 4.5% fallback
                logger.warning(f"Using fallback Treasury rate: 4.5%")
            
            # Calculate derived metrics
            conditions['average_correlation'] = 0.6  # TODO: Calculate from real correlation data
            conditions['volume_ratio'] = 1.0  # TODO: Calculate from real volume data  
            conditions['bid_ask_spread_ratio'] = 1.2  # TODO: Calculate from options data
            conditions['portfolio_return'] = 0.0  # Neutral for new analysis
            
            # Determine volatility regime
            vix = conditions['vix']
            if vix < 15:
                conditions['volatility_regime'] = 'low'
            elif vix < 25:
                conditions['volatility_regime'] = 'medium'
            elif vix < 40:
                conditions['volatility_regime'] = 'high'
            else:
                conditions['volatility_regime'] = 'extreme'
            
            # Add metadata
            conditions['data_timestamp'] = datetime.now().isoformat()
            conditions['data_source'] = type(self.manager.primary).__name__
            conditions['is_real_data'] = spy_override is None and vix_override is None
            conditions['circuit_breaker_state'] = self.circuit_breaker.state
            
            # Validate data quality
            if not self.validate_data_quality(conditions):
                raise DataValidationError(
                    'MarketDataService',
                    'market_conditions',
                    'invalid_data',
                    'valid market conditions'
                )
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, conditions, memory_ttl=300, persist_to_file=True)
            
            # Reset error tracking on successful fetch  
            self._error_count = 0
            
            logger.info(f"Successfully fetched market conditions: SPY=${conditions['spy_price']:.2f}, VIX={conditions['vix']:.1f}, Rate={conditions['risk_free_rate']:.1%}")
            
            return conditions
            
        except Exception as e:
            self._handle_error(f"Error fetching market conditions: {e}")
            
            # Return fallback data
            return self._get_fallback_market_conditions(symbol, vix_override, spy_override)
    
    def get_historical_market_data(self, 
                                 start_date: date,
                                 end_date: date,
                                 symbols: List[str] = None) -> pd.DataFrame:
        """Get historical market data for scenario analysis.
        
        Args:
            start_date: Start date for historical data
            end_date: End date for historical data  
            symbols: List of symbols to fetch (defaults to ['SPY', '^VIX'])
            
        Returns:
            DataFrame with historical data
        """
        if symbols is None:
            symbols = ['SPY', '^VIX']
        
        cache_key = f"historical_{start_date}_{end_date}_{'_'.join(symbols)}"
        
        # Check cache with longer TTL for historical data (1 day)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Using cached historical data for {symbols}")
                return cached
        
        try:
            logger.info(f"Fetching historical data for {symbols} from {start_date} to {end_date}")
            
            historical_data = {}
            
            for symbol in symbols:
                try:
                    if symbol == '^VIX':
                        # For VIX, get historical data and extract closing prices
                        data = self.manager.primary.get_historical_data(symbol, start_date, end_date)
                        if not data.empty:
                            historical_data['vix'] = data['Close']
                    elif symbol == 'SPY':
                        # For SPY, calculate daily returns
                        data = self.manager.primary.get_historical_data(symbol, start_date, end_date)
                        if not data.empty:
                            returns = data['Close'].pct_change().dropna()
                            historical_data['spy_return'] = returns
                    else:
                        # Generic symbol handling
                        data = self.manager.primary.get_historical_data(symbol, start_date, end_date)
                        if not data.empty:
                            historical_data[f'{symbol.lower()}_close'] = data['Close']
                            historical_data[f'{symbol.lower()}_return'] = data['Close'].pct_change().dropna()
                
                except Exception as e:
                    logger.warning(f"Failed to fetch historical data for {symbol}: {e}")
                    continue
            
            if len(historical_data) == 0:
                logger.warning("No historical data fetched, using simulated data")
                return self._get_simulated_historical_data(start_date, end_date)
            
            # Create DataFrame from collected data
            df = pd.DataFrame(historical_data)
            
            # Fill missing data with forward fill, then backward fill
            df = df.ffill().bfill()
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, df)
            
            logger.info(f"Successfully fetched historical data: {len(df)} rows, {list(df.columns)} columns")
            
            return df
            
        except Exception as e:
            self._handle_error(f"Error fetching historical data: {e}")
            return self._get_simulated_historical_data(start_date, end_date)
    
    def get_crisis_period_data(self, crisis_name: str = "covid_2020") -> pd.DataFrame:
        """Get historical data for specific crisis periods.
        
        Args:
            crisis_name: Name of crisis period ('covid_2020', 'volmageddon_2018', 'financial_2008')
            
        Returns:
            DataFrame with crisis period data
        """
        crisis_periods = {
            'covid_2020': (date(2020, 1, 1), date(2020, 6, 30)),
            'volmageddon_2018': (date(2018, 1, 1), date(2018, 4, 30)),
            'financial_2008': (date(2008, 6, 1), date(2009, 6, 30))
        }
        
        if crisis_name not in crisis_periods:
            logger.warning(f"Unknown crisis period: {crisis_name}")
            return pd.DataFrame()
        
        start_date, end_date = crisis_periods[crisis_name]
        logger.info(f"Fetching data for {crisis_name} crisis period: {start_date} to {end_date}")
        
        return self.get_historical_market_data(start_date, end_date)
    
    def validate_data_quality(self, data: Dict[str, Any]) -> bool:
        """Validate market data quality and detect stale/invalid data.
        
        Args:
            data: Market data dictionary to validate
            
        Returns:
            True if data passes quality checks
        """
        try:
            # Check required fields
            required_fields = ['spy_price', 'vix', 'risk_free_rate']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Validate ranges
            if not (50 <= data['spy_price'] <= 1000):  # Reasonable SPY range
                logger.warning(f"SPY price out of reasonable range: {data['spy_price']}")
                return False
            
            if not (5 <= data['vix'] <= 100):  # VIX should be 5-100
                logger.warning(f"VIX level out of reasonable range: {data['vix']}")
                return False
            
            if not (0 <= data['risk_free_rate'] <= 0.15):  # Rate should be 0-15%
                logger.warning(f"Risk-free rate out of reasonable range: {data['risk_free_rate']}")
                return False
            
            # Check data freshness
            if 'data_timestamp' in data:
                timestamp = datetime.fromisoformat(data['data_timestamp'].replace('Z', '+00:00'))
                age_minutes = (datetime.now() - timestamp).total_seconds() / 60
                if age_minutes > 60:  # Data older than 1 hour
                    logger.warning(f"Data is {age_minutes:.1f} minutes old")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return False
    
    def _handle_error(self, error_msg: str) -> None:
        """Handle and log errors with circuit breaker logic."""
        self._error_count += 1
        self._last_error_time = time.time()
        
        if self._error_count >= 3:
            logger.error(f"Multiple API failures detected. {error_msg}")
        else:
            logger.warning(error_msg)
    
    def _get_fallback_market_conditions(self, 
                                      symbol: str,
                                      vix_override: Optional[float] = None,
                                      spy_override: Optional[float] = None) -> Dict[str, Any]:
        """Get fallback market conditions when real data fails."""
        logger.info("Using fallback market conditions due to API failures")
        
        conditions = {
            'spy_price': spy_override or 420.0,
            'vix': vix_override or 22.5,
            'risk_free_rate': 0.045,  # 4.5% default
            'average_correlation': 0.6,
            'volume_ratio': 1.0,
            'bid_ask_spread_ratio': 1.2,
            'portfolio_return': 0.0,
            'volatility_regime': 'medium',  # Conservative default
            'data_timestamp': datetime.now().isoformat(),
            'data_source': 'fallback',
            'is_real_data': False
        }
        
        return conditions
    
    def _get_simulated_historical_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Generate simulated historical data as fallback."""
        import numpy as np
        
        logger.info(f"Generating simulated historical data from {start_date} to {end_date}")
        
        dates = pd.date_range(start_date, end_date, freq='D')
        np.random.seed(42)  # Reproducible results
        
        # Simulate VIX and SPY data with realistic characteristics
        vix_data = np.random.lognormal(mean=np.log(20), sigma=0.6, size=len(dates))
        vix_data = np.clip(vix_data, 10, 100)
        
        # SPY returns with correlation to VIX
        spy_returns = np.random.normal(0.0008, 0.012, size=len(dates))
        for i in range(1, len(vix_data)):
            if vix_data[i] > 40:  # Crisis conditions
                spy_returns[i] = np.random.normal(-0.025, 0.035)
        
        return pd.DataFrame({
            'vix': vix_data,
            'spy_return': spy_returns
        }, index=dates)
    
    def is_healthy(self) -> bool:
        """Check if the service is healthy and able to fetch data."""
        circuit_healthy = not self.circuit_breaker.is_open()
        error_rate_healthy = self._error_count < 5 or (time.time() - self._last_error_time) > 300
        
        return circuit_healthy and error_rate_healthy
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status including circuit breaker and error metrics."""
        error_stats = error_metrics.get_stats()
        
        return {
            'is_healthy': self.is_healthy(),
            'circuit_breaker': {
                'state': self.circuit_breaker.state,
                'failure_count': self.circuit_breaker.failure_count,
                'is_open': self.circuit_breaker.is_open()
            },
            'error_metrics': {
                'local_error_count': self._error_count,
                'last_error_time': self._last_error_time,
                'global_error_stats': error_stats
            },
            'cache_stats': self.cache.get_stats() if self.cache else None,
            'providers': {
                'primary': type(self.manager.primary).__name__,
                'fallback': type(self.manager.fallback).__name__
            }
        }