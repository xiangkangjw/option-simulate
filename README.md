# Options Trading Simulation Tool - Universa-Style Tail Hedging

## Overview

This application simulates options trading strategies with a focus on tail risk hedging, following the principles pioneered by Universa Investments. The primary strategy involves purchasing out-of-the-money (OTM) put options as portfolio insurance against market crashes and black swan events.

## Universa Investment Strategy Background

### Core Philosophy
- **Tail Risk Hedging**: Protect against rare but catastrophic market events (3+ standard deviation moves)
- **Asymmetric Risk/Reward**: Small, consistent costs for massive protection during crashes
- **Black Swan Protection**: Insurance against unpredictable, high-impact market events

### Key Strategy Components

#### 1. Put Option Selection
- **Strike Selection**: 10-20% out-of-the-money puts on broad market indices
- **Expiration**: Typically 30-90 days to expiration for optimal time decay vs. protection balance
- **Underlying**: Focus on SPY, QQQ, IWM (broad US market exposure)
- **Allocation**: 3-5% of total portfolio value allocated to put protection

#### 2. Rolling Strategy
- **Systematic Rolling**: Replace expiring puts with new positions
- **Strike Adjustment**: Maintain consistent percentage OTM based on current market levels
- **Timing**: Roll 2-3 weeks before expiration to avoid rapid time decay

#### 3. Cost Management
- **Premium Efficiency**: Focus on cheap, liquid options with high gamma
- **Volatility Timing**: Increase allocation during low VIX periods when puts are cheap
- **Dynamic Sizing**: Adjust position sizes based on market conditions

## Application Features

### Core Functionality
1. **Options Pricing Engine**
   - Black-Scholes-Merton model implementation
   - Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
   - Implied volatility calculations

2. **Portfolio Simulation**
   - Tail hedging strategy implementation
   - Dynamic position sizing
   - Automatic rolling logic
   - Transaction cost modeling

3. **Backtesting Engine**
   - Historical performance analysis
   - Stress testing against major market events
   - Risk-adjusted return metrics
   - Drawdown protection analysis

4. **Real-time Monitoring**
   - Current position tracking
   - Greeks monitoring
   - P&L attribution
   - Risk metrics dashboard

### Data Sources
- **Primary**: Free APIs (Yahoo Finance, Alpha Vantage)
- **Future Integration**: Premium data providers (Bloomberg, Refinitiv, CBOE)
- **Historical Data**: Market crashes (1987, 2000, 2008, 2020) for backtesting

## Technical Architecture

### Technology Stack
- **CLI Tool**: Python with Click and Rich for terminal interface
- **Data**: Pandas, NumPy for analysis
- **Options Pricing**: py-vollib for Black-Scholes calculations
- **Data Sources**: Yahoo Finance (free), Alpha Vantage (premium)
- **Configuration**: Pydantic for settings management

### Key Modules
1. **Data Provider**: Abstracted interface for multiple data sources
2. **Options Pricing**: Black-Scholes models with Greeks calculations
3. **Strategy Engine**: Tail hedging logic implementation
4. **Portfolio Simulation**: Position tracking and P&L calculations
5. **CLI Interface**: Rich terminal interface with tables and progress bars

## Risk Metrics & Performance

### Key Performance Indicators
- **Protection Ratio**: Portfolio value preserved during market crashes
- **Cost of Insurance**: Annual premium cost as % of portfolio
- **Sharpe Ratio**: Risk-adjusted returns with and without hedging
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Tail Risk Reduction**: VaR and CVaR improvements

### Stress Testing Scenarios
- **Black Monday (1987)**: -22.6% single day drop
- **Dot-com Crash (2000-2002)**: -49% peak-to-trough
- **Financial Crisis (2007-2009)**: -57% peak-to-trough  
- **COVID Crash (2020)**: -34% rapid decline

## Expected Outcomes

### Historical Context
During major market crashes, properly implemented tail hedging has shown:
- **2008 Financial Crisis**: 100-300% returns on put positions
- **COVID-19 Crash**: 400-1000% returns during March 2020 decline
- **Annual Cost**: Typically 1-3% of portfolio value in stable markets

### Strategic Benefits
1. **Psychological Comfort**: Ability to stay invested during volatility
2. **Opportunity Creation**: Capital available for buying during crashes
3. **Risk Reduction**: Lower overall portfolio volatility
4. **Asymmetric Payoff**: Limited downside, unlimited protection upside

## Getting Started

### Prerequisites
- Python 3.8+
- Internet connection for market data
- Optional: API keys for premium data providers

### Quick Installation & Setup
```bash
# 1. Clone or navigate to the repository
cd option-simulate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Test basic functionality
python test_basic.py

# 4. Install CLI tool
pip install -e .

# 5. Verify installation
options-sim --help
```

### CLI Usage

#### Basic Commands
```bash
# View current configuration
options-sim config

# Analyze options chain for tail hedging opportunities
options-sim analyze --symbol SPY

# Run strategy simulation (dry run - no actual trades)
options-sim run --portfolio-value 100000 --hedge-allocation 0.05 --dry-run

# Execute strategy with custom parameters
options-sim run --portfolio-value 50000 --symbols "SPY,QQQ" --otm-percentage 0.18
```

#### Command Options

**Analyze Command:**
```bash
options-sim analyze [OPTIONS]
  --symbol, -s          Symbol to analyze (default: SPY)
  --otm-percentage, -o  Out-of-the-money percentage (default: 0.15)
  --provider, -d        Data provider: yahoo|alphavantage (default: yahoo)
```

**Run Command:**
```bash
options-sim run [OPTIONS]
  --portfolio-value, -p  Initial portfolio value (default: 100000)
  --hedge-allocation, -a Allocation to hedging (default: 0.05)
  --otm-percentage, -o   Out-of-the-money percentage (default: 0.15)
  --symbols, -s         Comma-separated symbols (default: "SPY,QQQ,IWM")
  --provider, -d        Data provider (default: yahoo)
  --dry-run            Show strategy setup without executing
```

### Configuration

#### Environment Variables (Optional)
Create a `.env` file for premium data access:
```bash
# Copy example configuration
cp .env.example .env

# Edit with your API keys
ALPHA_VANTAGE_API_KEY=your_api_key_here
POLYGON_API_KEY=your_polygon_key_here

# Strategy parameters (optional overrides)
MAX_PORTFOLIO_ALLOCATION=0.05
DEFAULT_OTM_PERCENTAGE=0.15
DEFAULT_ROLLING_DAYS=21
```

#### Strategy Parameters
- **Portfolio Allocation**: 3-5% recommended for tail hedging
- **OTM Percentage**: 15-20% out-of-the-money for optimal cost/protection
- **Rolling Days**: Roll options 21 days before expiration
- **Target DTE**: 45 days to expiration for new positions

### Example Workflow
```bash
# 1. Check configuration
options-sim config

# 2. Analyze current market opportunities
options-sim analyze --symbol SPY --otm-percentage 0.15

# 3. Test strategy with your parameters
options-sim run --portfolio-value 250000 --hedge-allocation 0.04 --dry-run

# 4. Review the strategy configuration and proceed if satisfied
# Note: Live execution would require real options trading account
```

### Demo & Testing
```bash
# Run comprehensive demo with sample data
python demo.py

# Test individual components
python test_basic.py
```

## Disclaimer

This tool is for educational and simulation purposes only. Options trading involves substantial risk and is not suitable for all investors. Past performance does not guarantee future results. The strategies implemented here are based on publicly available information about tail hedging approaches and should not be considered investment advice.

## License

MIT License - See LICENSE file for details