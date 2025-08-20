#!/usr/bin/env python3
"""Basic test to verify the options simulator works."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from options_simulator.config import StrategyConfig, settings
    from options_simulator.data.providers import DataProviderFactory
    from options_simulator.models.options import BlackScholesCalculator
    
    print("✓ All imports successful")
    
    # Test configuration
    config = StrategyConfig(portfolio_value=50000, hedge_allocation=0.03)
    print(f"✓ Configuration created: ${config.portfolio_value:,.0f} portfolio, {config.hedge_allocation:.1%} hedge allocation")
    
    # Test data provider
    provider = DataProviderFactory.create_provider("yahoo")
    print("✓ Data provider created")
    
    # Test options calculator
    calculator = BlackScholesCalculator()
    
    # Calculate sample option price
    price = calculator.calculate_price(
        underlying_price=400.0,
        strike=380.0,
        time_to_expiry=0.25,  # 3 months
        risk_free_rate=0.05,
        volatility=0.20,
        option_type="put"
    )
    
    print(f"✓ Black-Scholes calculation: Put option price = ${price:.2f}")
    
    # Test Greeks calculation
    greeks = calculator.calculate_greeks(
        underlying_price=400.0,
        strike=380.0,
        time_to_expiry=0.25,
        risk_free_rate=0.05,
        volatility=0.20,
        option_type="put"
    )
    
    print(f"✓ Greeks calculation: Delta = {greeks.delta:.3f}, Gamma = {greeks.gamma:.3f}")
    
    print("\n🎉 Basic functionality test PASSED!")
    print("\nTo run the full CLI tool:")
    print("  pip install -e .")
    print("  options-sim --help")
    print("  options-sim analyze --symbol SPY")
    print("  options-sim run --portfolio-value 50000 --dry-run")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure to install dependencies: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)