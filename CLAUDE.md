# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for simulating Universa-style tail hedging strategies using out-of-the-money put options. The application focuses on portfolio protection against market crashes and black swan events through systematic put option purchases.

## Development Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Verify installation
options-sim --help
```

### Testing
```bash
# Run basic functionality test
python test_basic.py

# Run comprehensive demo
python demo.py

# Run pytest (if tests exist)
pytest
```

### Code Quality
```bash
# Format code with Black
black src/ test_basic.py demo.py

# Lint with flake8
flake8 src/ test_basic.py demo.py

# Type check with mypy
mypy src/
```

### CLI Usage
```bash
# View configuration
options-sim config

# Analyze options chain for tail hedging
options-sim analyze --symbol SPY --otm-percentage 0.15

# Run strategy simulation (dry run)
options-sim run --portfolio-value 100000 --hedge-allocation 0.05 --dry-run

# Execute with custom parameters
options-sim run --portfolio-value 50000 --symbols "SPY,QQQ" --otm-percentage 0.18
```

## Architecture

### Core Modules
- **src/options_simulator/config.py**: Settings management with Pydantic, environment variables, and strategy parameters
- **src/options_simulator/data/providers.py**: Abstracted data provider interface supporting Yahoo Finance and Alpha Vantage
- **src/options_simulator/models/options.py**: Black-Scholes pricing models, Greeks calculations, and option contracts
- **src/options_simulator/strategies/tail_hedging.py**: Core tail hedging strategy implementation, portfolio management, and position tracking
- **src/options_simulator/cli/main.py**: Rich-based CLI interface with Click commands

### Data Flow
1. CLI commands parse user input and create StrategyConfig
2. MarketDataManager fetches real-time data via configured provider (Yahoo Finance/Alpha Vantage)
3. TailHedgingStrategy executes put option selection and portfolio management
4. BlackScholesCalculator prices options and calculates Greeks
5. Results displayed via Rich tables and panels

### Key Strategy Components
- **Put Selection**: 10-20% OTM puts on broad market indices (SPY, QQQ, IWM)
- **Rolling Logic**: Replace expiring puts 21 days before expiration
- **Position Sizing**: 3-5% portfolio allocation to put protection
- **Risk Management**: Dynamic sizing based on market conditions

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `ALPHA_VANTAGE_API_KEY`: For premium data access
- `POLYGON_API_KEY`: Alternative data provider
- `MAX_PORTFOLIO_ALLOCATION`: Risk limit (default: 5%)
- `DEFAULT_OTM_PERCENTAGE`: Strike selection (default: 15%)
- `DEFAULT_ROLLING_DAYS`: Rolling frequency (default: 21)

### Key Files
- **requirements.txt**: Pinned dependencies including py-vollib, yfinance, rich, click
- **setup.py**: Package configuration with console_scripts entry point
- **.env.example**: Template for environment configuration

## Development Notes

- Uses py-vollib for Black-Scholes calculations and Greeks
- Yahoo Finance is the primary free data source
- Rich library provides terminal UI with tables and progress bars
- Pydantic handles configuration validation and settings management
- Strategy follows Universa Investments principles for tail risk hedging