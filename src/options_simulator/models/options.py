"""Options pricing models and Greeks calculations."""

import numpy as np
from scipy.stats import norm
from typing import Dict, NamedTuple
from dataclasses import dataclass
from datetime import datetime, date
import py_vollib.black_scholes as bs
import py_vollib.black_scholes.greeks.analytical as greeks


@dataclass
class OptionContract:
    """Represents an options contract."""
    symbol: str
    underlying: str
    strike: float
    expiration: date
    option_type: str  # 'call' or 'put'
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: int = 0
    open_interest: int = 0


class OptionGreeks(NamedTuple):
    """Greeks for an option position."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class BlackScholesCalculator:
    """Black-Scholes options pricing and Greeks calculator."""
    
    @staticmethod
    def days_to_expiration(expiration_date: date) -> float:
        """Calculate days to expiration as a fraction of a year."""
        today = date.today()
        days = (expiration_date - today).days
        return max(days / 365.0, 0.001)  # Avoid division by zero
    
    @staticmethod
    def calculate_price(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> float:
        """Calculate Black-Scholes option price."""
        try:
            return bs.black_scholes(
                flag=option_type[0].lower(),  # 'c' or 'p'
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
        except Exception as e:
            print(f"Error calculating BS price: {e}")
            return 0.0
    
    @staticmethod
    def calculate_greeks(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str
    ) -> OptionGreeks:
        """Calculate all Greeks for an option."""
        try:
            flag = option_type[0].lower()
            
            delta = greeks.delta(
                flag=flag,
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
            
            gamma_val = greeks.gamma(
                flag=flag,
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
            
            theta_val = greeks.theta(
                flag=flag,
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
            
            vega_val = greeks.vega(
                flag=flag,
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
            
            rho_val = greeks.rho(
                flag=flag,
                S=underlying_price,
                K=strike,
                t=time_to_expiry,
                r=risk_free_rate,
                sigma=volatility
            )
            
            return OptionGreeks(
                delta=delta,
                gamma=gamma_val,
                theta=theta_val,
                vega=vega_val,
                rho=rho_val
            )
            
        except Exception as e:
            print(f"Error calculating Greeks: {e}")
            return OptionGreeks(0.0, 0.0, 0.0, 0.0, 0.0)


class ImpliedVolatilityCalculator:
    """Calculate implied volatility from market prices."""
    
    @staticmethod
    def calculate_iv(
        market_price: float,
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> float:
        """Calculate implied volatility using Newton-Raphson method."""
        
        # Initial guess
        sigma = 0.2
        
        for _ in range(max_iterations):
            # Calculate price and vega with current sigma
            price = BlackScholesCalculator.calculate_price(
                underlying_price, strike, time_to_expiry, 
                risk_free_rate, sigma, option_type
            )
            
            if abs(price - market_price) < tolerance:
                return sigma
            
            # Calculate vega for Newton-Raphson iteration
            greeks_val = BlackScholesCalculator.calculate_greeks(
                underlying_price, strike, time_to_expiry,
                risk_free_rate, sigma, option_type
            )
            
            if abs(greeks_val.vega) < 1e-10:  # Avoid division by zero
                break
                
            # Newton-Raphson update
            sigma = sigma - (price - market_price) / greeks_val.vega
            
            # Keep sigma within reasonable bounds
            sigma = max(0.001, min(sigma, 5.0))
        
        return sigma


class TailHedgingAnalyzer:
    """Analyzer for tail hedging strategy performance."""
    
    @staticmethod
    def calculate_protection_ratio(
        portfolio_value: float,
        put_position_value: float,
        market_decline_pct: float
    ) -> float:
        """Calculate how much portfolio value is protected during market decline."""
        portfolio_loss = portfolio_value * market_decline_pct
        protection_provided = put_position_value
        return min(protection_provided / portfolio_loss, 1.0) if portfolio_loss > 0 else 0.0
    
    @staticmethod
    def calculate_hedge_cost_annual(
        total_premiums_paid: float,
        portfolio_value: float,
        time_period_days: int
    ) -> float:
        """Calculate annualized cost of hedging as percentage of portfolio."""
        annual_cost = (total_premiums_paid / portfolio_value) * (365 / time_period_days)
        return annual_cost
    
    @staticmethod
    def stress_test_scenarios() -> Dict[str, float]:
        """Return historical market crash scenarios for stress testing."""
        return {
            "Black Monday 1987": -0.226,
            "Dot-com Crash Peak": -0.49,
            "Financial Crisis 2008": -0.57,
            "COVID-19 Crash 2020": -0.34,
            "Flash Crash 2010": -0.09,
            "Normal Correction": -0.10,
            "Severe Correction": -0.20
        }