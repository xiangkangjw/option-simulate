"""Backtesting engine for tail hedging strategies."""

from typing import Dict, List, Tuple
from datetime import date, timedelta
import pandas as pd
from dataclasses import dataclass

from .strategies.tail_hedging import TailHedgingStrategy
from .data.providers import MarketDataManager
from .config import StrategyConfig
from .models.options import TailHedgingAnalyzer


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    start_date: date
    end_date: date
    initial_value: float
    final_value: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    hedge_cost_annual: float
    num_trades: int
    performance_during_crashes: Dict[str, float]


class HistoricalBacktester:
    """Backtesting engine for historical strategy performance."""
    
    def __init__(self, config: StrategyConfig, data_manager: MarketDataManager):
        self.config = config
        self.data_manager = data_manager
        self.analyzer = TailHedgingAnalyzer()
    
    def run_backtest(
        self, start_date: date, end_date: date, rebalance_frequency: int = 30
    ) -> BacktestResult:
        """Run a historical backtest."""
        
        # Initialize strategy
        strategy = TailHedgingStrategy(self.config, self.data_manager)
        
        # Get historical data for all symbols
        historical_data = {}
        for symbol in self.config.underlying_symbols:
            hist = self.data_manager.primary.get_historical_data(symbol, start_date, end_date)
            if not hist.empty:
                historical_data[symbol] = hist
        
        if not historical_data:
            raise ValueError("No historical data available for backtesting")
        
        # Run simulation day by day
        current_date = start_date
        performance_history = []
        
        while current_date <= end_date:
            # Get market data for current date
            market_data = {}
            for symbol, data in historical_data.items():
                if current_date.strftime('%Y-%m-%d') in data.index.strftime('%Y-%m-%d'):
                    price = data.loc[data.index.date == current_date, 'Close'].iloc[0]
                    market_data[symbol] = price
            
            if market_data:
                # Run strategy step
                try:
                    strategy.run_strategy_step(market_data)
                    
                    # Record performance
                    summary = strategy.get_performance_summary()
                    performance_history.append({
                        'date': current_date,
                        'portfolio_value': summary['current_value'],
                        'options_value': sum(pos['current_value'] for pos in summary['current_positions']),
                        'hedge_allocation': summary['options_allocation']
                    })
                except Exception as e:
                    print(f"Error on {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        # Calculate results
        return self._calculate_backtest_results(strategy, performance_history, start_date, end_date)
    
    def _calculate_backtest_results(
        self, strategy: TailHedgingStrategy, performance_history: List[Dict], 
        start_date: date, end_date: date
    ) -> BacktestResult:
        """Calculate backtest results and metrics."""
        
        if not performance_history:
            raise ValueError("No performance data to analyze")
        
        summary = strategy.get_performance_summary()
        
        # Basic metrics
        initial_value = self.config.portfolio_value
        final_value = summary['current_value']
        total_return = (final_value - initial_value) / initial_value
        
        # Calculate max drawdown
        values = [p['portfolio_value'] for p in performance_history]
        peak = values[0]
        max_drawdown = 0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (simplified)
        returns = []
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            returns.append(daily_return)
        
        if returns:
            avg_return = sum(returns) / len(returns)
            return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = (avg_return * 252) / (return_std * (252 ** 0.5)) if return_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate hedge cost
        days_elapsed = (end_date - start_date).days
        hedge_cost_annual = self.analyzer.calculate_hedge_cost_annual(
            summary['total_premiums_paid'], initial_value, days_elapsed
        )
        
        # Analyze performance during known crash periods
        crash_performance = self._analyze_crash_periods(performance_history)
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_value=initial_value,
            final_value=final_value,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            hedge_cost_annual=hedge_cost_annual,
            num_trades=summary['num_trades'],
            performance_during_crashes=crash_performance
        )
    
    def _analyze_crash_periods(self, performance_history: List[Dict]) -> Dict[str, float]:
        """Analyze strategy performance during historical crash periods."""
        
        # Define major crash periods (approximate dates)
        crash_periods = {
            "COVID-19 Crash 2020": (date(2020, 2, 19), date(2020, 3, 23)),
            "Financial Crisis 2008": (date(2008, 9, 15), date(2008, 11, 20)),
            "Dot-com Crash 2000": (date(2000, 3, 10), date(2000, 4, 14)),
        }
        
        crash_performance = {}
        
        for crash_name, (start_crash, end_crash) in crash_periods.items():
            # Find performance data during crash period
            crash_data = [
                p for p in performance_history 
                if start_crash <= p['date'] <= end_crash
            ]
            
            if len(crash_data) >= 2:
                start_value = crash_data[0]['portfolio_value']
                end_value = crash_data[-1]['portfolio_value']
                crash_return = (end_value - start_value) / start_value
                crash_performance[crash_name] = crash_return
        
        return crash_performance


def stress_test_strategy(
    config: StrategyConfig, data_manager: MarketDataManager
) -> Dict[str, float]:
    """Run stress tests against various market scenarios."""
    
    analyzer = TailHedgingAnalyzer()
    scenarios = analyzer.stress_test_scenarios()
    
    # Simulate strategy performance under each scenario
    strategy = TailHedgingStrategy(config, data_manager)
    
    results = {}
    
    for scenario_name, market_decline in scenarios.items():
        # Simulate market decline
        # This is a simplified stress test - in practice you'd model the full scenario
        
        # Assume SPY is primary hedge
        spy_price = data_manager.get_stock_price("SPY")
        if spy_price == 0:
            continue
        
        # Calculate expected put option payoff during crash
        avg_strike = spy_price * (1 - config.otm_percentage)
        new_spy_price = spy_price * (1 + market_decline)  # Market decline is negative
        
        if new_spy_price < avg_strike:
            # Put is in the money
            put_payoff = avg_strike - new_spy_price
            protection_ratio = analyzer.calculate_protection_ratio(
                config.portfolio_value,
                put_payoff * (config.hedge_capital / (spy_price * 0.02)),  # Rough estimate
                abs(market_decline)
            )
            results[scenario_name] = protection_ratio
        else:
            # Put expires worthless
            results[scenario_name] = 0.0
    
    return results