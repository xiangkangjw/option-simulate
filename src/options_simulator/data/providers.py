"""Data providers for market data and options chains."""

import yfinance as yf
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
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def _rate_limit(self):
        """Implement rate limiting to avoid 429 errors."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            # Add small random delay to avoid synchronized requests
            sleep_time += random.uniform(0.1, 0.5)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_stock_price(self, symbol: str) -> float:
        """Get current stock price from Yahoo Finance."""
        self._rate_limit()
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Try multiple approaches for getting current price
            # 1. First try fast_info (most reliable with new yfinance version)
            try:
                fast_info = ticker.fast_info
                if hasattr(fast_info, 'last_price') and fast_info.last_price:
                    return float(fast_info.last_price)
            except Exception as fast_error:
                print(f"Fast info method failed for {symbol}: {fast_error}")
            
            # 2. Fallback to ticker.info
            try:
                info = ticker.info
                if 'regularMarketPrice' in info and info['regularMarketPrice']:
                    return float(info['regularMarketPrice'])
                elif 'previousClose' in info and info['previousClose']:
                    return float(info['previousClose'])
            except Exception as info_error:
                print(f"Info method failed for {symbol}: {info_error}")
            
            # 3. Try yf.download as fallback
            try:
                data = yf.download(symbol, period="1d", interval="1d", progress=False, auto_adjust=True)
                if not data.empty:
                    return float(data['Close'].iloc[-1])
            except Exception as download_error:
                print(f"Download method failed for {symbol}: {download_error}")
            
            # 4. Last resort - try historical data
            try:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
            except Exception as hist_error:
                print(f"History method failed for {symbol}: {hist_error}")
            
            return 0.0
            
        except requests.exceptions.HTTPError as http_error:
            if "429" in str(http_error):
                print(f"Rate limited for {symbol}. Consider using a longer delay between requests.")
                # Exponential backoff for rate limiting
                time.sleep(random.uniform(2, 5))
                return 0.0
            else:
                print(f"HTTP error fetching stock price for {symbol}: {http_error}")
                return 0.0
        except requests.exceptions.JSONDecodeError as json_error:
            print(f"JSON decode error for {symbol} (Yahoo may be rate limiting): {json_error}")
            return 0.0
        except Exception as e:
            print(f"Error fetching stock price for {symbol}: {e}")
            return 0.0
    
    def get_options_chain(self, symbol: str, expiration: str = None) -> List[OptionContract]:
        """Get options chain from Yahoo Finance."""
        self._rate_limit()
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates with error handling
            try:
                available_expirations = ticker.options
                if not available_expirations:
                    print(f"No options available for {symbol}")
                    return []
                
                if expiration:
                    if expiration in available_expirations:
                        expirations = [expiration]
                    else:
                        print(f"Expiration {expiration} not available for {symbol}")
                        return []
                else:
                    # Filter expirations to target 21-90 DTE range for tail hedging
                    from datetime import datetime as dt, date
                    today = date.today()
                    filtered_expirations = []
                    for exp_str in available_expirations:
                        try:
                            exp_date = dt.strptime(exp_str, '%Y-%m-%d').date()
                            dte = (exp_date - today).days
                            if 21 <= dte <= 90:  # Target range for tail hedging
                                filtered_expirations.append(exp_str)
                        except ValueError:
                            continue
                    
                    expirations = filtered_expirations[:5] if filtered_expirations else available_expirations[:3]
                    
            except requests.exceptions.JSONDecodeError as json_error:
                print(f"JSON decode error getting expirations for {symbol}: {json_error}")
                return []
            except Exception as exp_error:
                print(f"Error getting option expirations for {symbol}: {exp_error}")
                return []
            
            contracts = []
            
            for exp_date in expirations:
                try:
                    # Add rate limiting between expiration date requests
                    if len(contracts) > 0:  # Only sleep after first request
                        time.sleep(0.5)
                    
                    chain = ticker.option_chain(exp_date)
                    
                    # Process puts (primary focus for tail hedging)
                    for _, put in chain.puts.iterrows():
                        try:
                            contract = OptionContract(
                                symbol=put.get('contractSymbol', ''),
                                underlying=symbol,
                                strike=safe_float(put.get('strike'), 0),
                                expiration=datetime.strptime(exp_date, '%Y-%m-%d').date(),
                                option_type='put',
                                bid=safe_float(put.get('bid'), 0),
                                ask=safe_float(put.get('ask'), 0),
                                last=safe_float(put.get('lastPrice'), 0),
                                volume=safe_int(put.get('volume'), 0),
                                open_interest=safe_int(put.get('openInterest'), 0)
                            )
                            contracts.append(contract)
                        except Exception as contract_error:
                            print(f"Error creating put contract for {symbol}: {contract_error}")
                            continue
                    
                    # Also include calls for completeness
                    for _, call in chain.calls.iterrows():
                        try:
                            contract = OptionContract(
                                symbol=call.get('contractSymbol', ''),
                                underlying=symbol,
                                strike=safe_float(call.get('strike'), 0),
                                expiration=datetime.strptime(exp_date, '%Y-%m-%d').date(),
                                option_type='call',
                                bid=safe_float(call.get('bid'), 0),
                                ask=safe_float(call.get('ask'), 0),
                                last=safe_float(call.get('lastPrice'), 0),
                                volume=safe_int(call.get('volume'), 0),
                                open_interest=safe_int(call.get('openInterest'), 0)
                            )
                            contracts.append(contract)
                        except Exception as contract_error:
                            print(f"Error creating call contract for {symbol}: {contract_error}")
                            continue
                        
                except requests.exceptions.JSONDecodeError as json_error:
                    print(f"JSON decode error processing expiration {exp_date} for {symbol}: {json_error}")
                    continue
                except Exception as e:
                    print(f"Error processing expiration {exp_date}: {e}")
                    continue
            
            return contracts
            
        except requests.exceptions.HTTPError as http_error:
            if "429" in str(http_error):
                print(f"Rate limited getting options for {symbol}. Consider using a longer delay.")
                time.sleep(random.uniform(3, 6))
            else:
                print(f"HTTP error fetching options chain for {symbol}: {http_error}")
            return []
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