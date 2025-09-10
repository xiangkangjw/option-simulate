"""Custom exception hierarchy for the options simulator.

This module provides a comprehensive set of exceptions for handling
various error conditions in data providers, API failures, and validation.
"""

from typing import Optional, Dict, Any
import time


class OptionsSimulatorError(Exception):
    """Base exception class for all options simulator errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = time.time()
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class DataProviderError(OptionsSimulatorError):
    """Base exception for data provider related errors."""
    
    def __init__(self, message: str, provider: str, symbol: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.symbol = symbol
        self.context.update({'provider': provider, 'symbol': symbol})


class APIRateLimitError(DataProviderError):
    """Exception raised when API rate limits are exceeded."""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None, **kwargs):
        message = f"API rate limit exceeded for {provider}"
        if retry_after:
            message += f" (retry after {retry_after} seconds)"
        super().__init__(message, provider, **kwargs)
        self.retry_after = retry_after


class APIConnectionError(DataProviderError):
    """Exception raised when API connection fails."""
    
    def __init__(self, provider: str, url: Optional[str] = None, **kwargs):
        message = f"Failed to connect to {provider}"
        if url:
            message += f" at {url}"
        super().__init__(message, provider, **kwargs)
        self.url = url


class InvalidAPIKeyError(DataProviderError):
    """Exception raised when API key is invalid or missing."""
    
    def __init__(self, provider: str, **kwargs):
        message = f"Invalid or missing API key for {provider}"
        super().__init__(message, provider, **kwargs)


class DataValidationError(DataProviderError):
    """Exception raised when data validation fails."""
    
    def __init__(self, provider: str, field: str, value: Any, expected: str, **kwargs):
        message = f"Data validation failed for {provider}: {field}={value} (expected {expected})"
        super().__init__(message, provider, **kwargs)
        self.field = field
        self.value = value
        self.expected = expected


class StaleDataError(DataProviderError):
    """Exception raised when data is too stale."""
    
    def __init__(self, provider: str, age_seconds: float, max_age: float, **kwargs):
        message = f"Data from {provider} is too stale: {age_seconds:.1f}s old (max: {max_age:.1f}s)"
        super().__init__(message, provider, **kwargs)
        self.age_seconds = age_seconds
        self.max_age = max_age


class MarketDataUnavailableError(DataProviderError):
    """Exception raised when market data is unavailable."""
    
    def __init__(self, provider: str, symbol: str, data_type: str = "general", **kwargs):
        message = f"Market data unavailable from {provider}: {symbol} ({data_type})"
        super().__init__(message, provider, symbol, **kwargs)
        self.data_type = data_type


class ServiceUnavailableError(OptionsSimulatorError):
    """Exception raised when a service is unavailable."""
    
    def __init__(self, service_name: str, reason: Optional[str] = None, **kwargs):
        message = f"Service {service_name} is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.reason = reason


class ConfigurationError(OptionsSimulatorError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, setting: str, value: Any, reason: str, **kwargs):
        message = f"Configuration error for {setting}={value}: {reason}"
        super().__init__(message, **kwargs)
        self.setting = setting
        self.value = value
        self.reason = reason


class CalculationError(OptionsSimulatorError):
    """Exception raised for calculation-related errors."""
    
    def __init__(self, calculation_type: str, parameters: Dict[str, Any], reason: str, **kwargs):
        message = f"Calculation error in {calculation_type}: {reason}"
        super().__init__(message, **kwargs)
        self.calculation_type = calculation_type
        self.parameters = parameters
        self.reason = reason


class CircuitBreakerError(OptionsSimulatorError):
    """Exception raised when circuit breaker is triggered."""
    
    def __init__(self, service: str, failure_count: int, threshold: int, **kwargs):
        message = f"Circuit breaker triggered for {service}: {failure_count}/{threshold} failures"
        super().__init__(message, **kwargs)
        self.service = service
        self.failure_count = failure_count
        self.threshold = threshold


class CircuitBreaker:
    """Circuit breaker implementation for API failure management."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300.0):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery (seconds)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'closed'  # closed, open, half_open
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'open':
            if time.time() - self.last_failure_time < self.recovery_timeout:
                raise CircuitBreakerError(
                    service=func.__name__,
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold
                )
            else:
                self.state = 'half_open'
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'half_open':
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
    
    def reset(self):
        """Reset the circuit breaker to closed state."""
        self.failure_count = 0
        self.state = 'closed'
        self.last_failure_time = 0
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == 'open'


def handle_api_error(error: Exception, provider: str, symbol: Optional[str] = None) -> OptionsSimulatorError:
    """Convert generic API errors to specific exception types.
    
    Args:
        error: Original exception
        provider: Data provider name
        symbol: Symbol being requested (if applicable)
        
    Returns:
        Appropriate OptionsSimulatorError subclass
    """
    error_str = str(error).lower()
    
    if '429' in error_str or 'rate limit' in error_str:
        # Try to extract retry-after header if available
        retry_after = None
        if hasattr(error, 'response') and hasattr(error.response, 'headers'):
            retry_after = error.response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None
        
        return APIRateLimitError(provider, retry_after=retry_after, context={'original_error': str(error)})
    
    elif 'connection' in error_str or 'timeout' in error_str or 'unreachable' in error_str:
        return APIConnectionError(provider, context={'original_error': str(error)})
    
    elif 'unauthorized' in error_str or 'forbidden' in error_str or 'api key' in error_str:
        return InvalidAPIKeyError(provider, context={'original_error': str(error)})
    
    elif 'not found' in error_str or '404' in error_str:
        return MarketDataUnavailableError(provider, symbol or 'unknown', context={'original_error': str(error)})
    
    else:
        # Generic data provider error
        return DataProviderError(f"API error: {error}", provider, symbol, context={'original_error': str(error)})


class ErrorMetrics:
    """Track error metrics for monitoring and alerting."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
        self.start_time = time.time()
    
    def record_error(self, error: OptionsSimulatorError):
        """Record an error for metrics tracking."""
        error_type = error.error_code
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        self.error_history.append({
            'timestamp': error.timestamp,
            'error_type': error_type,
            'message': error.message,
            'context': error.context
        })
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
    
    def get_error_rate(self, window_seconds: float = 3600) -> float:
        """Get error rate for the specified time window."""
        current_time = time.time()
        recent_errors = [
            e for e in self.error_history 
            if current_time - e['timestamp'] <= window_seconds
        ]
        return len(recent_errors) / window_seconds  # errors per second
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'total_errors': len(self.error_history),
            'error_counts': self.error_counts.copy(),
            'error_rate_1h': self.get_error_rate(3600),
            'error_rate_24h': self.get_error_rate(86400),
            'most_recent_error': self.error_history[-1] if self.error_history else None
        }


# Global error metrics instance
error_metrics = ErrorMetrics()