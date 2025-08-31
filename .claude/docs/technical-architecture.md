# Technical Architecture - Options Trading Simulation Tool

## System Overview

The Options Trading Simulation Tool is a Python CLI application that implements Universa-style tail hedging strategies. The system is designed around modular components that handle data acquisition, options pricing, strategy execution, and risk management.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │  Strategy Engine │    │ Data Providers  │
│   (Rich/Click)  │────│  (Tail Hedging)  │────│ (Yahoo/Alpha-V) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Configuration  │    │ Options Models   │    │   Backtesting   │
│   (Pydantic)    │    │ (Black-Scholes)  │    │     Engine      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. Configuration Layer (`config.py`)

**Purpose**: Centralized settings management with environment variable support

**Key Classes**:
- `Settings`: Global application settings using Pydantic BaseSettings
- `StrategyConfig`: Strategy-specific parameters with derived calculations

**Configuration Sources**:
- Environment variables (`.env` file support)
- Default values for development
- CLI parameter overrides

**Key Settings**:
```python
# Risk management
MAX_PORTFOLIO_ALLOCATION=0.05  # 5% max hedge allocation
DEFAULT_OTM_PERCENTAGE=0.15    # 15% out-of-the-money
DEFAULT_ROLLING_DAYS=21        # Roll 21 days before expiry

# API keys
ALPHA_VANTAGE_API_KEY=...
POLYGON_API_KEY=...
```

### 2. Data Provider Layer (`data/providers.py`)

**Purpose**: Abstracted interface for multiple market data sources

**Architecture Pattern**: Abstract Factory + Strategy Pattern

**Key Classes**:
- `DataProvider` (ABC): Base interface for all providers
- `YahooFinanceProvider`: Free data source implementation
- `AlphaVantageProvider`: Premium data source implementation
- `DataProviderFactory`: Creates provider instances
- `MarketDataManager`: Coordinates multiple providers with fallback logic

**Data Flow**:
1. CLI requests market data
2. MarketDataManager selects primary provider
3. Provider fetches real-time prices and options chains
4. Data validated and transformed to internal models
5. Fallback to secondary providers on failures

**Rate Limiting**: Built-in retry logic and exponential backoff for API stability

### 3. Options Pricing Models (`models/options.py`)

**Purpose**: Mathematical models for options pricing and risk calculations

**Key Components**:

**OptionContract**: Data model for options contracts
```python
@dataclass
class OptionContract:
    symbol: str           # Option symbol
    underlying: str       # Stock symbol
    strike: float         # Strike price
    expiration: date      # Expiration date
    option_type: str      # 'call' or 'put'
    bid/ask/last: float   # Market prices
    volume/open_interest: int  # Liquidity metrics
```

**BlackScholesCalculator**: Core pricing engine
- Uses `py-vollib` library for accuracy
- Calculates option prices and Greeks
- Handles edge cases (near expiration, extreme strikes)

**Greeks Calculation**:
- Delta: Price sensitivity to underlying movement
- Gamma: Delta sensitivity (convexity)
- Theta: Time decay
- Vega: Volatility sensitivity
- Rho: Interest rate sensitivity

**TailHedgingAnalyzer**: Strategy-specific calculations
- Protection ratio analysis
- Stress testing scenarios
- Cost-benefit calculations

### 4. Strategy Engine (`strategies/tail_hedging.py`)

**Purpose**: Core implementation of Universa-style tail hedging

**Key Classes**:

**Position**: Individual options position tracking
```python
@dataclass
class Position:
    contract: OptionContract
    quantity: int
    entry_price: float
    entry_date: date
    current_value: float = 0.0
    pnl: float = 0.0
```

**Portfolio**: Aggregate portfolio management
- Cash management
- Stock value tracking
- Options positions
- Total value calculation
- Allocation monitoring

**TailHedgingStrategy**: Main strategy orchestrator
- Position entry/exit logic
- Rolling schedule management
- Risk limit enforcement
- Performance tracking

**Strategy Logic**:
1. **Entry Criteria**:
   - Target 15-20% OTM puts
   - 30-90 days to expiration
   - Minimum liquidity thresholds
   - Maximum allocation limits

2. **Rolling Logic**:
   - Monitor days to expiration
   - Roll 21 days before expiry
   - Adjust strikes for new market levels
   - Maintain consistent hedge ratio

3. **Risk Management**:
   - Portfolio allocation limits (3-5%)
   - Position size limits
   - Liquidity requirements
   - Maximum loss thresholds

### 5. CLI Interface (`cli/main.py`)

**Purpose**: User interface built with Rich and Click libraries

**Command Structure**:
- `options-sim config`: Display current settings
- `options-sim analyze`: Analyze options opportunities
- `options-sim run`: Execute strategy (dry-run or live)
- `options-sim backtest`: Historical performance analysis

**UI Components**:
- Rich tables for data display
- Progress spinners for long operations
- Color-coded output (green/red for P&L)
- Panel layouts for configuration

### 6. Backtesting Engine (`backtesting.py`)

**Purpose**: Historical strategy performance analysis

**Key Features**:
- Historical data replay
- Transaction cost modeling
- Performance metrics calculation
- Stress testing against major market events

**Metrics Calculated**:
- Total return
- Sharpe ratio
- Maximum drawdown
- Annual hedge cost
- Protection ratio during crashes

## Data Flow Architecture

### 1. Strategy Execution Flow
```
User CLI Input → StrategyConfig → MarketDataManager → Strategy Engine
                      ↓
Performance Results ← Portfolio Updates ← Options Pricing ← Market Data
```

### 2. Options Selection Process
```
Market Data → Current Prices → Strike Calculation → Options Chain Fetch
                    ↓
Selected Options ← Liquidity Filter ← Greeks Analysis ← Price Filter
```

### 3. Risk Management Flow
```
Portfolio State → Allocation Check → Position Sizing → Risk Limits
                        ↓
Trade Execution ← Validation ← Cost Analysis ← Liquidity Check
```

## Key Design Patterns

### 1. Abstract Factory Pattern
- `DataProviderFactory` creates provider instances
- Supports multiple data sources with consistent interface
- Easy to add new providers

### 2. Strategy Pattern
- Different data providers implement same interface
- Pluggable risk management rules
- Configurable strategy parameters

### 3. Observer Pattern
- Portfolio monitors position updates
- Strategy tracks market data changes
- Performance metrics calculated on state changes

## Technical Stack

### Core Dependencies
- **py-vollib**: Black-Scholes calculations and Greeks
- **yfinance**: Yahoo Finance API integration
- **scipy/numpy**: Mathematical computations
- **pandas**: Data manipulation and analysis

### CLI Framework
- **click**: Command-line interface framework
- **rich**: Terminal UI with tables and colors
- **tabulate**: Data formatting

### Configuration
- **pydantic**: Settings validation and type safety
- **python-dotenv**: Environment variable management

### Development Tools
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing framework

## Security Considerations

### API Key Management
- Environment variables for sensitive data
- `.env.example` template without secrets
- Optional API key validation

### Data Validation
- Pydantic models for input validation
- Safe type conversion utilities
- Error handling for malformed data

### Risk Controls
- Portfolio allocation limits
- Position size restrictions
- Maximum loss thresholds
- Sanity checks on pricing data

## Performance Characteristics

### Data Access Patterns
- Caching of market data within sessions
- Rate limiting for API calls
- Batch requests where possible
- Fallback providers for reliability

### Computational Efficiency
- Vectorized calculations using NumPy
- Efficient pandas operations
- Lazy loading of historical data
- Minimal memory footprint for CLI usage

## Extension Points

### Adding New Data Providers
1. Inherit from `DataProvider` ABC
2. Implement required methods
3. Register with `DataProviderFactory`
4. Add to CLI provider choices

### Adding New Strategies
1. Create strategy class following `TailHedgingStrategy` pattern
2. Implement position management interface
3. Add configuration parameters
4. Integrate with CLI commands

### Adding New Option Models
1. Extend `BlackScholesCalculator` or create new calculator
2. Implement pricing and Greeks methods
3. Add to strategy selection logic
4. Update configuration options