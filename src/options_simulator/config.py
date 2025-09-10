"""Configuration settings for the options simulator."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Data Provider API Keys
    alpha_vantage_api_key: Optional[str] = Field(None, env="ALPHA_VANTAGE_API_KEY")
    polygon_api_key: Optional[str] = Field(None, env="POLYGON_API_KEY")
    quandl_api_key: Optional[str] = Field(None, env="QUANDL_API_KEY")
    
    # Application Settings
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Strategy Parameters - Universa-style Configuration
    max_portfolio_allocation: float = Field(0.03, env="MAX_PORTFOLIO_ALLOCATION")  # Reduced to institutional optimal 3%
    default_rolling_days: int = Field(21, env="DEFAULT_ROLLING_DAYS")
    default_otm_percentage: float = Field(0.30, env="DEFAULT_OTM_PERCENTAGE")  # Updated to Universa crisis protection level
    
    # Universa-style OTM ranges for different protection types
    volatility_protection_otm: float = Field(0.15, env="VOLATILITY_PROTECTION_OTM")  # 15% OTM for volatility spikes
    crisis_protection_otm: float = Field(0.30, env="CRISIS_PROTECTION_OTM")          # 30% OTM for true tail hedging
    extreme_crisis_otm: float = Field(0.35, env="EXTREME_CRISIS_OTM")              # 35% OTM for maximum protection
    
    # Simulation Settings
    initial_portfolio_value: float = Field(100000.0, env="INITIAL_PORTFOLIO_VALUE")
    transaction_cost_per_contract: float = Field(1.00, env="TRANSACTION_COST_PER_CONTRACT")
    slippage_bps: int = Field(5, env="SLIPPAGE_BPS")
    
    # Market Data Settings
    risk_free_rate: float = Field(0.05, env="RISK_FREE_RATE")  # 5% default
    default_volatility: float = Field(0.20, env="DEFAULT_VOLATILITY")  # 20% default
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


class StrategyConfig:
    """Configuration for Universa-style tail hedging strategy."""
    
    def __init__(
        self,
        portfolio_value: float = None,
        hedge_allocation: float = None,
        otm_percentage: float = None,
        rolling_days: int = None,
        underlying_symbols: list = None,
    ):
        self.portfolio_value = portfolio_value or settings.initial_portfolio_value
        self.hedge_allocation = hedge_allocation or settings.max_portfolio_allocation
        self.otm_percentage = otm_percentage or settings.default_otm_percentage
        self.rolling_days = rolling_days or settings.default_rolling_days
        self.underlying_symbols = underlying_symbols or ["SPY", "QQQ", "IWM"]
        
        # Derived settings
        self.hedge_capital = self.portfolio_value * self.hedge_allocation
        self.min_dte = 30  # Minimum days to expiration
        self.max_dte = 90  # Maximum days to expiration
        self.target_dte = 45  # Target days to expiration for new positions
        
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "portfolio_value": self.portfolio_value,
            "hedge_allocation": self.hedge_allocation,
            "otm_percentage": self.otm_percentage,
            "rolling_days": self.rolling_days,
            "underlying_symbols": self.underlying_symbols,
            "hedge_capital": self.hedge_capital,
            "min_dte": self.min_dte,
            "max_dte": self.max_dte,
            "target_dte": self.target_dte,
        }


class EnhancedHedgingConfig:
    """Enhanced configuration for advanced tail hedging strategies with regime awareness."""
    
    def __init__(self, config_dict: Optional[dict] = None):
        """Initialize enhanced hedging configuration."""
        config = config_dict or {}
        
        # Original settings
        self.default_expiration_months = config.get("default_expiration_months", [2, 3, 6, 12])
        self.default_otm_percentages = config.get("default_otm_percentages", [0.12, 0.15, 0.18, 0.20])
        self.transaction_cost_per_contract = config.get("transaction_cost_per_contract", 5.0)
        self.commission_rate = config.get("commission_rate", 0.65)
        self.default_rolling_threshold = config.get("default_rolling_threshold", 21)
        
        # Volatility regime settings
        self.vix_regime_thresholds = config.get("vix_regime_thresholds", {
            "low": 15, 
            "medium": 25, 
            "high": 40, 
            "extreme": 60
        })
        
        self.volatility_regime_multipliers = config.get("volatility_regime_multipliers", {
            "low": 1.0, 
            "medium": 1.3, 
            "high": 1.8, 
            "extreme": 2.5
        })
        
        # Exit strategy settings
        self.default_exit_triggers = config.get("default_exit_triggers", [
            "vix_spike", "portfolio_protection", "time_decay"
        ])
        
        self.vix_spike_thresholds = config.get("vix_spike_thresholds", {
            "moderate": 30, 
            "severe": 45, 
            "extreme": 60
        })
        
        self.profit_taking_thresholds = config.get("profit_taking_thresholds", [2.0, 5.0, 10.0])
        
        # Jump diffusion parameters
        self.default_jump_intensity = config.get("default_jump_intensity", 0.1)  # jumps per year
        self.default_jump_mean = config.get("default_jump_mean", -0.05)  # -5% average jump
        self.default_jump_volatility = config.get("default_jump_volatility", 0.15)  # 15% jump volatility
        
        # Advanced modeling settings
        self.enable_stochastic_volatility = config.get("enable_stochastic_volatility", True)
        self.enable_correlation_breakdown = config.get("enable_correlation_breakdown", True)
        self.monte_carlo_simulations = config.get("monte_carlo_simulations", 10000)
        
        # Performance settings
        self.cache_calculations = config.get("cache_calculations", True)
        self.parallel_processing = config.get("parallel_processing", True)
        self.max_workers = config.get("max_workers", 4)
        
        # Data provider settings
        self.primary_data_provider = config.get("primary_data_provider", "yahoo")
        self.fallback_data_provider = config.get("fallback_data_provider", "yahoo")
        self.enable_data_caching = config.get("enable_data_caching", True)
        self.data_freshness_threshold = config.get("data_freshness_threshold", 300)  # 5 minutes
        
        # Historical data settings
        self.historical_data_start = config.get("historical_data_start", "2020-01-01")
        self.historical_data_end = config.get("historical_data_end", "2023-12-31")
        self.crisis_periods = config.get("crisis_periods", {
            "covid_2020": {"start": "2020-01-01", "end": "2020-06-30", "name": "COVID-19 Crisis"},
            "volmageddon_2018": {"start": "2018-01-01", "end": "2018-04-30", "name": "Volmageddon 2018"},
            "financial_2008": {"start": "2008-06-01", "end": "2009-06-30", "name": "Financial Crisis 2008"}
        })
        
        # Market hours and validation
        self.validate_market_hours = config.get("validate_market_hours", True)
        self.handle_holidays = config.get("handle_holidays", True)
        self.data_quality_checks = config.get("data_quality_checks", True)
        
    def get_regime_config(self, regime: str) -> dict:
        """Get configuration specific to a volatility regime."""
        return {
            "threshold": self.vix_regime_thresholds.get(regime, 25),
            "multiplier": self.volatility_regime_multipliers.get(regime, 1.0),
            "exit_triggers": self._get_regime_exit_triggers(regime)
        }
    
    def _get_regime_exit_triggers(self, regime: str) -> list:
        """Get exit triggers appropriate for a specific regime."""
        if regime == "low":
            return ["time_decay"]
        elif regime == "medium":
            return ["profit_target", "time_decay"]
        elif regime == "high":
            return ["vix_spike", "profit_target", "portfolio_protection"]
        else:  # extreme
            return ["vix_spike", "profit_target", "portfolio_protection", "correlation_breakdown"]
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "default_expiration_months": self.default_expiration_months,
            "default_otm_percentages": self.default_otm_percentages,
            "transaction_cost_per_contract": self.transaction_cost_per_contract,
            "commission_rate": self.commission_rate,
            "default_rolling_threshold": self.default_rolling_threshold,
            "vix_regime_thresholds": self.vix_regime_thresholds,
            "volatility_regime_multipliers": self.volatility_regime_multipliers,
            "default_exit_triggers": self.default_exit_triggers,
            "vix_spike_thresholds": self.vix_spike_thresholds,
            "profit_taking_thresholds": self.profit_taking_thresholds,
            "default_jump_intensity": self.default_jump_intensity,
            "default_jump_mean": self.default_jump_mean,
            "default_jump_volatility": self.default_jump_volatility,
            "enable_stochastic_volatility": self.enable_stochastic_volatility,
            "enable_correlation_breakdown": self.enable_correlation_breakdown,
            "monte_carlo_simulations": self.monte_carlo_simulations,
            "cache_calculations": self.cache_calculations,
            "parallel_processing": self.parallel_processing,
            "max_workers": self.max_workers
        }
    
    @classmethod
    def from_strategy_config(cls, strategy_config: StrategyConfig) -> "EnhancedHedgingConfig":
        """Create enhanced config from basic strategy config."""
        return cls({
            "transaction_cost_per_contract": 5.0,  # Default enhanced settings
            "default_otm_percentages": [strategy_config.otm_percentage],
            "default_rolling_threshold": strategy_config.rolling_days
        })
