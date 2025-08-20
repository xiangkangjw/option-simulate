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
    
    # Strategy Parameters
    max_portfolio_allocation: float = Field(0.05, env="MAX_PORTFOLIO_ALLOCATION")
    default_rolling_days: int = Field(21, env="DEFAULT_ROLLING_DAYS")
    default_otm_percentage: float = Field(0.15, env="DEFAULT_OTM_PERCENTAGE")
    
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