"""Data providers for market data and options chains."""

# yfinance library removed - using alternative Yahoo Finance API only
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import time
import random
from ..config import settings
from ..models.options import OptionContract


def safe_float(value, default=0.0):
    """Safely convert value to float, handling NaN and None."""
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Safely convert value to int, handling NaN and None."""
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))  # Convert to float first to handle string numbers
    except (ValueError, TypeError):
        return default


class DataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    def get_stock_price(self, symbol: str) -> float:
        """Get current stock price."""
        pass
    
    @abstractmethod
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Get options chain for a symbol."""
        pass
    
    @abstractmethod
    def get_historical_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get historical price data."""
        pass


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider using yfinance library."""
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Increased to 2 seconds between requests
        self.consecutive_failures = 0
        self.backoff_multiplier = 1.0
    
    def _rate_limit(self):
        """Implement adaptive rate limiting with exponential backoff."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Calculate adaptive delay based on recent failures
        adaptive_interval = self.min_request_interval * self.backoff_multiplier
        
        if time_since_last_request < adaptive_interval:
            sleep_time = adaptive_interval - time_since_last_request
            # Add random jitter to avoid synchronized requests
            sleep_time += random.uniform(0.2, 1.0)
            print(f"Rate limiting: sleeping {sleep_time:.1f}s (backoff: {self.backoff_multiplier:.1f}x)")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _record_success(self):
        """Record a successful API call and reduce backoff."""
        self.consecutive_failures = 0
        self.backoff_multiplier = max(1.0, self.backoff_multiplier * 0.9)
    
    def _record_failure(self):
        """Record a failed API call and increase backoff."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 2:
            self.backoff_multiplier = min(8.0, self.backoff_multiplier * 2.0)
            print(f"Increasing backoff to {self.backoff_multiplier:.1f}x after {self.consecutive_failures} failures")
    
    def _get_price_alternative_api(self, symbol: str) -> float:
        """Get price using alternative Yahoo Finance API endpoint."""
        url_symbol = symbol.replace('^', '%5E')  # URL encode ^ symbols
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{url_symbol}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    if 'meta' in result and 'regularMarketPrice' in result['meta']:
                        price = float(result['meta']['regularMarketPrice'])
                        print(f"Alternative API success for {symbol}: ${price:.2f}")
                        return price
        except Exception as e:
            print(f"Alternative API failed for {symbol}: {e}")
        
        return 0.0
    
    def get_stock_price(self, symbol: str) -> float:
        """Get current stock price from Yahoo Finance using alternative API only."""
        self._rate_limit()
        
        # Use alternative API (proven to work without yfinance dependency)
        print(f"Fetching {symbol} using alternative Yahoo Finance API...")
        price = self._get_price_alternative_api(symbol)
        if price > 0:
            self._record_success()
            return price
        else:
            self._record_failure()
            print(f"Failed to fetch price for {symbol}")
            return 0.0
    
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Get options chain from Yahoo Finance."""
        self._rate_limit()
        
        # yfinance is disabled, return empty list for now
        # TODO: Implement options chain via alternative API if available
        print(f"Options chain not available without yfinance dependency for {symbol}")
        return []
    
    def get_historical_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get historical price data from Yahoo Finance using alternative API."""
        self._rate_limit()
        
        # Convert dates to timestamps
        start_timestamp = int(start_date.strftime('%s'))
        end_timestamp = int(end_date.strftime('%s'))
        
        url_symbol = symbol.replace('^', '%5E')  # URL encode ^ symbols
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{url_symbol}'
        
        params = {
            'period1': start_timestamp,
            'period2': end_timestamp,
            'interval': '1d',
            'includePrePost': 'true',
            'events': 'div,splits'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and data['chart']['result']:
                    result = data['chart']['result'][0]
                    
                    # Extract timestamps and price data
                    timestamps = result['timestamp']
                    quotes = result['indicators']['quote'][0]
                    
                    # Build DataFrame
                    df_data = {
                        'Open': quotes.get('open', []),
                        'High': quotes.get('high', []),
                        'Low': quotes.get('low', []),
                        'Close': quotes.get('close', []),
                        'Volume': quotes.get('volume', [])
                    }
                    
                    # Create DataFrame with proper datetime index
                    df = pd.DataFrame(df_data)
                    df.index = pd.to_datetime(timestamps, unit='s')
                    
                    # Clean the data
                    df = df.dropna()
                    
                    print(f"Successfully fetched {len(df)} days of historical data for {symbol}")
                    self._record_success()
                    return df
                    
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            self._record_failure()
            
        return pd.DataFrame()

    def get_vix_level(self) -> float:
        """Get current VIX level from Yahoo Finance."""
        return self.get_stock_price("^VIX")
    
    def get_treasury_rate(self, tenor: str = "10Y") -> float:
        """Get Treasury yield for specified tenor.
        
        Args:
            tenor: Treasury tenor (3M, 6M, 2Y, 10Y, 30Y)
            
        Returns:
            Treasury yield as decimal (e.g., 0.045 for 4.5%)
        """
        self._rate_limit()
        
        # Map tenor to Yahoo Finance symbols
        tenor_symbols = {
            "3M": "^IRX",    # 3-Month Treasury
            "6M": "^IRX",    # Use 3M as proxy for 6M
            "2Y": "^TNX",    # Use 10Y as proxy for 2Y  
            "10Y": "^TNX",   # 10-Year Treasury Note
            "30Y": "^TYX"    # 30-Year Treasury Bond
        }
        
        symbol = tenor_symbols.get(tenor, "^TNX")
        
        try:
            # Use alternative API to get Treasury rate
            rate = self._get_price_alternative_api(symbol)
            if rate > 0 and rate < 15:  # Reasonable rate range (0-15% as percentage)
                return rate / 100.0  # Convert percentage to decimal
            
            # Default fallback for common rates if API fails
            defaults = {"3M": 0.045, "10Y": 0.045, "30Y": 0.048}
            return defaults.get(tenor, 0.045)
            
        except Exception as e:
            print(f"Error fetching Treasury rate for {tenor}: {e}")
            return 0.045  # 4.5% default


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider for premium data."""
    
    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_stock_price(self, symbol: str) -> float:
        """Get current stock price from Alpha Vantage."""
        if not self.api_key:
            print("Alpha Vantage API key not configured")
            return 0.0
        
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Global Quote" in data:
                price = data["Global Quote"]["05. price"]
                return float(price)
            return 0.0
            
        except Exception as e:
            print(f"Error fetching stock price from Alpha Vantage: {e}")
            return 0.0
    
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Alpha Vantage doesn't provide options data in free tier."""
        print("Options chain not available through Alpha Vantage free tier")
        return []
    
    def get_historical_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get historical data from Alpha Vantage."""
        if not self.api_key:
            print("Alpha Vantage API key not configured")
            return pd.DataFrame()
        
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "full",
                "apikey": self.api_key
            }
            
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            if "Time Series (Daily)" not in data:
                return pd.DataFrame()
            
            # Convert to DataFrame and filter by date range
            df = pd.DataFrame.from_dict(
                data["Time Series (Daily)"], orient="index"
            )
            df.index = pd.to_datetime(df.index)
            df.columns = ["Open", "High", "Low", "Close", "Volume"]
            df = df.astype(float)
            
            # Filter by date range
            mask = (df.index.date >= start_date) & (df.index.date <= end_date)
            return df.loc[mask]
            
        except Exception as e:
            print(f"Error fetching historical data from Alpha Vantage: {e}")
            return pd.DataFrame()

    def get_vix_level(self) -> float:
        """Get current VIX level from Alpha Vantage."""
        return self.get_stock_price("VIX")  # Alpha Vantage uses VIX without ^
    
    def get_treasury_rate(self, tenor: str = "10Y") -> float:
        """Get Treasury yield - Alpha Vantage has limited support for Treasury data.
        
        Args:
            tenor: Treasury tenor (not fully supported by Alpha Vantage)
            
        Returns:
            Treasury yield as decimal, defaults to 4.5% if not available
        """
        if not self.api_key:
            print("Alpha Vantage API key not configured for Treasury rates")
            return 0.045
            
        # Alpha Vantage has limited Treasury data support
        # For production, consider using FRED API for Treasury rates
        print(f"Alpha Vantage Treasury rate support limited, using default for {tenor}")
        return 0.045  # Default 4.5%


class DataProviderFactory:
    """Factory for creating data providers."""
    
    @staticmethod
    def create_provider(provider_type: str = "yahoo") -> DataProvider:
        """Create a data provider instance."""
        if provider_type.lower() == "yahoo":
            return YahooFinanceProvider()
        elif provider_type.lower() == "alphavantage":
            return AlphaVantageProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    @staticmethod
    def get_best_available_provider() -> DataProvider:
        """Get the best available data provider based on configuration."""
        # Try premium providers first if API keys are available
        if settings.alpha_vantage_api_key:
            print("Using Alpha Vantage data provider")
            return AlphaVantageProvider()
        
        # Fall back to free providers
        print("Using Yahoo Finance data provider")
        return YahooFinanceProvider()


class MarketDataManager:
    """Manages market data from multiple providers."""
    
    def __init__(self, primary_provider: str = "yahoo", fallback_provider: str = "yahoo"):
        self.primary = DataProviderFactory.create_provider(primary_provider)
        self.fallback = DataProviderFactory.create_provider(fallback_provider)
    
    def get_stock_price(self, symbol: str) -> float:
        """Get stock price with fallback."""
        price = self.primary.get_stock_price(symbol)
        if price == 0.0 and self.primary != self.fallback:
            price = self.fallback.get_stock_price(symbol)
        return price
    
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Get options chain with fallback."""
        contracts = self.primary.get_options_chain(symbol, expiration)
        if not contracts and self.primary != self.fallback:
            contracts = self.fallback.get_options_chain(symbol, expiration)
        return contracts
    
    def get_tail_hedge_candidates(
        self, symbol: str, current_price: float, otm_percentage: float = 0.15
    ) -> List[OptionContract]:
        """Get put options suitable for tail hedging."""
        contracts = self.get_options_chain(symbol)
        
        print(f"\n=== Tail Hedge Analysis for {symbol} ===")
        print(f"Current price: ${current_price:.2f}")
        print(f"OTM percentage: {otm_percentage:.1%}")
        
        # Filter for puts that are out-of-the-money
        target_strike = current_price * (1 - otm_percentage)
        print(f"Target strike (max): ${target_strike:.2f}")
        
        print(f"\nTotal contracts retrieved: {len(contracts)}")
        
        # Count contracts by type
        put_count = sum(1 for c in contracts if c.option_type == 'put')
        call_count = sum(1 for c in contracts if c.option_type == 'call')
        print(f"Put contracts: {put_count}")
        print(f"Call contracts: {call_count}")
        
        if put_count == 0:
            print("❌ No put options found in options chain!")
            return []
        
        # Analyze put options in detail
        puts = [c for c in contracts if c.option_type == 'put']
        print(f"\n=== Analyzing {len(puts)} Put Options ===")
        
        # Show strike price distribution
        strikes = [c.strike for c in puts if c.strike > 0]
        if strikes:
            print(f"Strike range: ${min(strikes):.2f} - ${max(strikes):.2f}")
            strikes_below_target = [s for s in strikes if s <= target_strike]
            print(f"Strikes <= target (${target_strike:.2f}): {len(strikes_below_target)} out of {len(strikes)}")
        
        candidates = []
        filtered_out = {"strike_too_high": 0, "no_strike": 0, "no_price": 0}
        
        for contract in contracts:
            if contract.option_type != 'put':
                continue
                
            # Check strike price validity
            if contract.strike <= 0:
                filtered_out["no_strike"] += 1
                continue
                
            # Check if strike is within target range
            if contract.strike > target_strike:
                filtered_out["strike_too_high"] += 1
                continue
                
            # Check if any price is available
            has_price = (contract.bid > 0 or contract.ask > 0 or contract.last > 0)
            if not has_price:
                filtered_out["no_price"] += 1
                continue
                
            candidates.append(contract)
        
        # Print filtering results
        print(f"\n=== Filtering Results ===")
        print(f"✅ Candidates found: {len(candidates)}")
        print(f"❌ Filtered out - Strike too high (>${target_strike:.2f}): {filtered_out['strike_too_high']}")
        print(f"❌ Filtered out - No valid strike price: {filtered_out['no_strike']}")
        print(f"❌ Filtered out - No price data: {filtered_out['no_price']}")
        
        if candidates:
            print(f"\n=== Top 5 Candidates ===")
            # Sort by expiration date and liquidity
            candidates.sort(key=lambda x: (x.expiration, -x.volume))
            
            for i, contract in enumerate(candidates[:5]):
                dte = (contract.expiration - date.today()).days
                print(f"{i+1}. ${contract.strike:.0f} exp {contract.expiration} (DTE:{dte}) "
                      f"bid:${contract.bid:.2f} ask:${contract.ask:.2f} last:${contract.last:.2f} "
                      f"vol:{contract.volume} OI:{contract.open_interest}")
        else:
            print("\n❌ No suitable tail hedging options found after filtering")
            
            # Additional diagnostics
            if put_count > 0:
                print(f"\n=== Diagnostic Information ===")
                sample_puts = puts[:5]  # Show first 5 puts for debugging
                for i, put in enumerate(sample_puts):
                    dte = (put.expiration - date.today()).days
                    meets_strike = put.strike <= target_strike
                    has_price = (put.bid > 0 or put.ask > 0 or put.last > 0)
                    print(f"Put {i+1}: ${put.strike:.0f} exp {put.expiration} (DTE:{dte}) "
                          f"strike_ok:{meets_strike} price_ok:{has_price} "
                          f"bid:${put.bid:.2f} ask:${put.ask:.2f} last:${put.last:.2f}")
        
        return candidates

    def get_vix_level(self) -> float:
        """Get current VIX level with fallback."""
        try:
            vix = self.primary.get_vix_level()
            if vix > 0 and vix < 100:  # Reasonable VIX range
                return vix
        except Exception as e:
            print(f"Primary provider VIX fetch failed: {e}")
        
        # Try fallback provider
        if self.primary != self.fallback:
            try:
                vix = self.fallback.get_vix_level()
                if vix > 0 and vix < 100:
                    return vix
            except Exception as e:
                print(f"Fallback provider VIX fetch failed: {e}")
        
        print("Warning: Using default VIX level (20.0) due to API failures")
        return 20.0  # Conservative default
    
    def get_treasury_rate(self, tenor: str = "10Y") -> float:
        """Get Treasury rate with fallback."""
        try:
            rate = self.primary.get_treasury_rate(tenor)
            if 0 < rate < 0.15:  # Reasonable rate range (0-15%)
                return rate
        except Exception as e:
            print(f"Primary provider Treasury rate fetch failed: {e}")
        
        # Try fallback provider
        if self.primary != self.fallback:
            try:
                rate = self.fallback.get_treasury_rate(tenor)
                if 0 < rate < 0.15:
                    return rate
            except Exception as e:
                print(f"Fallback provider Treasury rate fetch failed: {e}")
        
        print(f"Warning: Using default {tenor} rate (4.5%) due to API failures")
        return 0.045  # Default 4.5%
    
    def get_market_conditions(self, symbol: str = "SPY") -> dict:
        """Get comprehensive current market conditions.
        
        Args:
            symbol: Primary equity symbol to analyze (default: SPY)
            
        Returns:
            Dictionary with market conditions including VIX, prices, and rates
        """
        conditions = {}
        
        # Get current equity price
        conditions['spy_price'] = self.get_stock_price(symbol)
        if conditions['spy_price'] == 0.0:
            print(f"Warning: Could not fetch {symbol} price, using default $420")
            conditions['spy_price'] = 420.0
        
        # Get VIX level
        conditions['vix'] = self.get_vix_level()
        
        # Get risk-free rate (10-year Treasury as primary)
        conditions['risk_free_rate'] = self.get_treasury_rate("10Y")
        
        # Calculate additional market metrics
        conditions['average_correlation'] = 0.6  # TODO: Calculate from real data
        conditions['volume_ratio'] = 1.0  # TODO: Calculate from volume data
        conditions['bid_ask_spread_ratio'] = 1.2  # TODO: Calculate from options data
        conditions['portfolio_return'] = 0.0  # Neutral for new analysis
        
        # Determine volatility regime based on VIX
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
        from datetime import datetime
        conditions['data_timestamp'] = datetime.now().isoformat()
        conditions['data_source'] = type(self.primary).__name__
        
        return conditions
