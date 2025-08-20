#!/usr/bin/env python3
"""Demo script showing the options simulator with sample data."""

import sys
import os
from datetime import date, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from options_simulator.config import StrategyConfig
from options_simulator.models.options import OptionContract, BlackScholesCalculator, TailHedgingAnalyzer
from options_simulator.strategies.tail_hedging import TailHedgingStrategy, Portfolio, Position

def demo_black_scholes():
    """Demonstrate Black-Scholes pricing."""
    print("=" * 60)
    print("BLACK-SCHOLES OPTIONS PRICING DEMO")
    print("=" * 60)
    
    calculator = BlackScholesCalculator()
    
    # SPY example: $420 current, $380 strike put, 60 days to expiry
    underlying_price = 420.0
    strike = 380.0  # ~10% OTM
    time_to_expiry = 60/365  # 60 days
    risk_free_rate = 0.05
    volatility = 0.20
    
    price = calculator.calculate_price(
        underlying_price, strike, time_to_expiry, risk_free_rate, volatility, "put"
    )
    
    greeks = calculator.calculate_greeks(
        underlying_price, strike, time_to_expiry, risk_free_rate, volatility, "put"
    )
    
    print(f"Underlying (SPY): ${underlying_price:.2f}")
    print(f"Strike: ${strike:.2f} ({(1-strike/underlying_price):.1%} OTM)")
    print(f"Time to Expiry: {int(time_to_expiry*365)} days")
    print(f"Volatility: {volatility:.1%}")
    print(f"\nPut Option Price: ${price:.2f}")
    print(f"Delta: {greeks.delta:.3f}")
    print(f"Gamma: {greeks.gamma:.4f}")
    print(f"Theta: ${greeks.theta:.2f} (daily decay)")
    print(f"Vega: ${greeks.vega:.2f} (per 1% vol change)")

def demo_tail_hedging_analysis():
    """Demonstrate tail hedging analysis."""
    print("\n" + "=" * 60)
    print("TAIL HEDGING STRATEGY ANALYSIS")
    print("=" * 60)
    
    analyzer = TailHedgingAnalyzer()
    
    # Portfolio parameters
    portfolio_value = 100000
    put_premium_cost = 2000  # $2000 spent on puts
    
    print(f"Portfolio Value: ${portfolio_value:,}")
    print(f"Hedge Cost: ${put_premium_cost:,} ({put_premium_cost/portfolio_value:.1%})")
    
    # Analyze protection during various market scenarios
    scenarios = analyzer.stress_test_scenarios()
    
    print(f"\nSTRESS TEST SCENARIOS:")
    print("-" * 40)
    
    # Assume puts are 15% OTM and provide 1:1 protection for moves beyond strike
    spy_price = 420.0
    put_strike = spy_price * 0.85  # 15% OTM
    put_contracts = 50  # Example position size
    
    for scenario, decline in scenarios.items():
        new_price = spy_price * (1 + decline)
        
        if new_price < put_strike:
            # Put is in-the-money
            put_payoff = (put_strike - new_price) * put_contracts * 100
            protection_ratio = analyzer.calculate_protection_ratio(
                portfolio_value, put_payoff, abs(decline)
            )
            print(f"{scenario:20}: {decline:+.1%} → Protection: {protection_ratio:.1%}")
        else:
            print(f"{scenario:20}: {decline:+.1%} → Protection: 0.0%")

def demo_portfolio_simulation():
    """Demonstrate portfolio simulation."""
    print("\n" + "=" * 60)
    print("PORTFOLIO SIMULATION DEMO")
    print("=" * 60)
    
    # Create sample portfolio
    portfolio = Portfolio(cash=95000, stock_value=95000)
    
    # Create sample put position
    sample_put = OptionContract(
        symbol="SPY240315P00380000",
        underlying="SPY",
        strike=380.0,
        expiration=date.today() + timedelta(days=45),
        option_type="put",
        bid=2.10,
        ask=2.20,
        last=2.15,
        volume=1500,
        open_interest=5000
    )
    
    # Create position
    position = Position(
        contract=sample_put,
        quantity=10,  # 10 contracts
        entry_price=2.15,
        entry_date=date.today()
    )
    
    # Simulate market move (SPY drops 5%)
    current_option_price = 8.50  # Put gained value due to market drop
    position.update_value(current_option_price)
    
    portfolio.positions.append(position)
    
    print(f"Portfolio Total Value: ${portfolio.total_value:,.0f}")
    print(f"Cash: ${portfolio.cash:,.0f}")
    print(f"Stock Value: ${portfolio.stock_value:,.0f}")
    print(f"Options Value: ${position.current_value:,.0f}")
    print(f"Options Allocation: {portfolio.options_allocation:.1%}")
    print(f"\nPosition P&L: ${position.pnl:,.0f}")
    print(f"Position Return: {(position.pnl/(position.entry_price * position.quantity * 100)):.1%}")

def demo_strategy_parameters():
    """Demonstrate strategy configuration."""
    print("\n" + "=" * 60)
    print("UNIVERSA STRATEGY PARAMETERS")
    print("=" * 60)
    
    config = StrategyConfig(
        portfolio_value=500000,
        hedge_allocation=0.04,  # 4%
        otm_percentage=0.18,    # 18% OTM
        rolling_days=21,
        underlying_symbols=["SPY", "QQQ"]
    )
    
    print(f"Portfolio Value: ${config.portfolio_value:,}")
    print(f"Hedge Allocation: {config.hedge_allocation:.1%}")
    print(f"Hedge Capital: ${config.hedge_capital:,}")
    print(f"Out-of-Money %: {config.otm_percentage:.1%}")
    print(f"Rolling Days: {config.rolling_days}")
    print(f"Target DTE: {config.target_dte} days")
    print(f"Underlying Symbols: {', '.join(config.underlying_symbols)}")
    
    # Calculate example position sizing
    spy_price = 420.0
    target_strike = spy_price * (1 - config.otm_percentage)
    put_price = 2.50  # Example price for 18% OTM put
    
    capital_per_symbol = config.hedge_capital / len(config.underlying_symbols)
    contracts_per_symbol = int(capital_per_symbol / (put_price * 100))
    
    print(f"\nEXAMPLE POSITION SIZING:")
    print(f"SPY Price: ${spy_price:.2f}")
    print(f"Target Strike: ${target_strike:.2f}")
    print(f"Put Price: ${put_price:.2f}")
    print(f"Capital per Symbol: ${capital_per_symbol:,.0f}")
    print(f"Contracts per Symbol: {contracts_per_symbol}")
    print(f"Total Premium Cost: ${contracts_per_symbol * put_price * 100 * len(config.underlying_symbols):,.0f}")

if __name__ == "__main__":
    demo_black_scholes()
    demo_tail_hedging_analysis()
    demo_portfolio_simulation()
    demo_strategy_parameters()
    
    print("\n" + "=" * 60)
    print("🎉 DEMO COMPLETE!")
    print("=" * 60)
    print("\nTo use the CLI tool:")
    print("  options-sim config              # View settings")
    print("  options-sim analyze --symbol QQQ # Analyze options")
    print("  options-sim run --dry-run       # Simulate strategy")
    print("\nNote: Live data requires internet connection")
    print("Configure API keys in .env file for premium data")