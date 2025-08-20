"""Data providers for market data and options chains."""

import yfinance as yf
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
from ..config import settings
from ..models.options import OptionContract


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
    
    def get_stock_price(self, symbol: str) -> float:
        """Get current stock price from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            return 0.0
        except Exception as e:
            print(f"Error fetching stock price for {symbol}: {e}")
            return 0.0
    
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Get options chain from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            if expiration:
                expirations = [expiration]
            else:
                expirations = ticker.options[:3]  # Get first 3 expirations
            
            contracts = []
            
            for exp_date in expirations:
                try:
                    chain = ticker.option_chain(exp_date)
                    
                    # Process puts (primary focus for tail hedging)
                    for _, put in chain.puts.iterrows():
                        contract = OptionContract(
                            symbol=put.get('contractSymbol', ''),
                            underlying=symbol,
                            strike=float(put.get('strike', 0)),
                            expiration=datetime.strptime(exp_date, '%Y-%m-%d').date(),
                            option_type='put',
                            bid=float(put.get('bid', 0)),
                            ask=float(put.get('ask', 0)),
                            last=float(put.get('lastPrice', 0)),
                            volume=int(put.get('volume', 0)),
                            open_interest=int(put.get('openInterest', 0))
                        )
                        contracts.append(contract)
                    
                    # Also include calls for completeness
                    for _, call in chain.calls.iterrows():
                        contract = OptionContract(
                            symbol=call.get('contractSymbol', ''),
                            underlying=symbol,
                            strike=float(call.get('strike', 0)),
                            expiration=datetime.strptime(exp_date, '%Y-%m-%d').date(),
                            option_type='call',
                            bid=float(call.get('bid', 0)),
                            ask=float(call.get('ask', 0)),
                            last=float(call.get('lastPrice', 0)),
                            volume=int(call.get('volume', 0)),
                            open_interest=int(call.get('openInterest', 0))
                        )
                        contracts.append(contract)
                        
                except Exception as e:
                    print(f"Error processing expiration {exp_date}: {e}")
                    continue
            
            return contracts
            
        except Exception as e:
            print(f"Error fetching options chain for {symbol}: {e}")
            return []
    
    def get_historical_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get historical price data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            return hist
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return pd.DataFrame()


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
        
        # Filter for puts that are out-of-the-money
        target_strike = current_price * (1 - otm_percentage)
        
        candidates = []
        for contract in contracts:
            if (contract.option_type == 'put' and 
                contract.strike <= target_strike and
                contract.bid > 0 and
                contract.volume > 0):
                candidates.append(contract)
        
        # Sort by expiration date and liquidity
        candidates.sort(key=lambda x: (x.expiration, -x.volume))
        
        return candidates