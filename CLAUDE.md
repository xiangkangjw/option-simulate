# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for simulating Universa-style tail hedging strategies using out-of-the-money put options. The application focuses on portfolio protection against market crashes and black swan events through systematic put option purchases.

## Rules

## Rules

- before you do any work, MUST view files in .claude/tasks/context_session_x.md file to get the full context (x being the id of the session we are operating in, if file doesn't exist, then create one)
- context_session_x.md should contain most of the context of what we did, overall plan, and sub agents will continuously add context to the file
- after you finish the work, MUST update/append the .claude/tasks/context_session_x.md to make sure others can get full context of what you did. you MUST preserve the existing conversation.
- whenever you use subagents, ask them to update the .claude/tasks/context_session_x.md with their findings

### Sub agents

You have access to 6 sub agents:

- quant-dev-advisor: Expert guidance on quantitative finance development, options pricing implementation, derivatives modeling, and tail hedging strategy optimization
- financial-data-engineer: Design and troubleshoot financial data infrastructure, API integrations, data pipelines, and caching systems for financial time series data
- cli-architect: CLI application development, software architecture patterns, performance optimization for computational tasks, and testing frameworks
- tail-hedge-portfolio-manager: Institutional-grade portfolio protection guidance, risk allocation strategies, and tail hedging portfolio management
- quant-researcher: Rigorous quantitative analysis, backtesting validation, statistical performance evaluation, and academic research on financial strategies
- fintech-product-manager: Financial technology product expertise, UX design for complex trading tools, go-to-market strategies, and sophisticated investor requirements

Your most important agents would be quant-dev-advisor and tail-hedge-portfolio-manager

Sub-agents will do research about the implementation, but you will do the actual implementation; when passing tasks to sub agent, make sure you pass the the context file, e.g. '.claude/tasks/session_context_x.md'.
After each sub agent finish the work, make sure you read the related documentation they created to get full context of the plan before you start executing.

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

# SPX hedge comparison (enhanced feature)
options-sim hedge-compare --portfolio-value 100000 --timeframes "3M,6M" --export-format csv
```

### Hedge Comparison Analysis

The `hedge-compare` command provides sophisticated analysis of different SPX put option strategies:

```bash
# Basic comparison
options-sim hedge-compare --portfolio-value 100000 --timeframes "3M,6M"

# Comprehensive analysis with all features
options-sim hedge-compare \
  --portfolio-value 100000 \
  --timeframes "2M,3M,6M,12M" \
  --otm-percentages "0\.12,0\.15,0\.18,0\.20" \
  --volatility-regime auto \
  --enable-dynamic-exits \
  --scenario-analysis \
  --jump-diffusion-pricing \
  --export-format csv

# Export results for analysis
options-sim hedge-compare --portfolio-value 100000 --timeframes "3M,6M" \
  --export-format csv --output hedge_analysis_\$\(date \+%Y%m%d\)\.csv
```

\*\*Key Features:\*\*
- \*\*Volatility regime analysis\*\*: Adjusts pricing based on current VIX environment
- \*\*Dynamic exit strategies\*\*: Models profit-taking opportunities during black swan events
- \*\*Jump-diffusion pricing\*\*: More accurate tail risk pricing vs Black-Scholes
- \*\*Comprehensive Greeks\*\*: Regime-adjusted risk sensitivities
- \*\*Export capabilities\*\*: CSV format for further analysis

\*\*Documentation Structure:\*\*
- \*\*Quick Start\*\*: `docs/hedge-compare-quick-start\.md` - Get results in 5 minutes
- \*\*User Guide\*\*: `docs/hedge-compare-user-guide\.md` - Complete educational guide for CFA L1\+ users
- \*\*Decision Framework\*\*: `docs/hedge-strategy-decision-framework\.md` - Systematic approach to strategy selection
- \*\*CSV Export Guide\*\*: `docs/hedge-comparison-export-guide\.md` - Understanding all output fields and metrics
- \*\*Technical Implementation\*\*: `docs/spx-hedging-comparison-implementation\.md` - Mathematical models and advanced features
```

## Architecture

You should refer to .claude/docs/technical-architecture.md

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
