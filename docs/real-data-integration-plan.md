# Real Market Data Integration Plan

## Project Overview
Transform the hedge-compare command from mock data simulation to institutional-grade real market data integration through a 4-phase implementation approach, leveraging existing MarketDataManager infrastructure.

## Current State
- **hedge-compare command** currently uses mock data:
  - Hardcoded VIX = 22.5
  - Hardcoded SPY price = $420.00
  - Simulated historical data using numpy.random
- **Existing infrastructure** includes full MarketDataManager with Yahoo Finance and Alpha Vantage providers
- **Strong foundation** with proper abstractions and error handling already in place

## Implementation Phases

### Phase 1: Core Data Infrastructure Enhancement (Week 1-2)

#### 1.1 Extend Existing Data Providers
**Files to modify:**
- `src/options_simulator/data/providers.py`

**New methods to add:**
- `YahooFinanceProvider.get_vix_level()` - fetch ^VIX symbol
- `YahooFinanceProvider.get_treasury_rate(tenor)` - fetch ^TNX, ^IRX, ^FVX
- `AlphaVantageProvider.get_vix_level()` - VIX via Alpha Vantage API
- `MarketDataManager.get_market_conditions()` - comprehensive market snapshot

#### 1.2 Create Service Layer Architecture
**New files to create:**
- `src/options_simulator/services/__init__.py`
- `src/options_simulator/services/market_data_service.py`
- `src/options_simulator/services/service_factory.py`

**Service layer responsibilities:**
- Clean separation between CLI and data logic
- Dependency injection for testability
- Async data fetching with Rich progress indicators
- Intelligent caching (5-minute TTL for real-time, daily for historical)

#### 1.3 Replace Mock Functions
**Files to modify:**
- `src/options_simulator/cli/hedge_compare.py`

**Functions to replace:**
- `_create_market_conditions()` - use real VIX and SPY prices via MarketDataService
- Keep override parameters (`--vix-level`, `--spy-price`) for testing
- Graceful fallback to mock data on API failures

### Phase 2: Historical Data Integration (Week 3)

#### 2.1 Real Historical Scenario Analysis
**Files to modify:**
- `src/options_simulator/cli/hedge_compare.py`

**Replace `_get_sample_historical_data()` function:**
- Fetch actual VIX and SPY data (2020-2023) via Yahoo Finance
- Focus on crisis periods: March 2020, Feb 2018 Volmageddon, Oct 2008
- Data quality validation and gap filling
- Maintain simulation fallback for offline usage

#### 2.2 Enhanced Configuration
**Files to modify:**
- `src/options_simulator/config.py`

**Extend `EnhancedHedgingConfig` with:**
- Primary/fallback provider configuration
- Data freshness thresholds and validation rules
- API key management for premium sources
- Market hours awareness and holiday handling

### Phase 3: CLI Enhancement & Error Handling (Week 4)

#### 3.1 New CLI Options
**Files to modify:**
- `src/options_simulator/cli/hedge_compare.py`

**New CLI parameters:**
- `--use-real-data/--use-mock-data` (default: real)
- `--data-provider` choice (yahoo, alpha_vantage)
- `--max-data-age` for staleness tolerance in seconds
- Enhanced user feedback showing data source and quality

#### 3.2 Robust Error Handling
**New files to create:**
- `src/options_simulator/exceptions.py`
- `src/options_simulator/data/cache.py`

**Error handling features:**
- Custom exception hierarchy for data provider failures
- Circuit breaker pattern for API rate limiting
- Graceful degradation with clear user messaging
- Comprehensive logging for troubleshooting

### Phase 4: Advanced Features & Testing (Week 5-6)

#### 4.1 Volatility Regime Enhancement
**Files to modify:**
- `src/options_simulator/analysis/volatility_regime.py` (if exists)
- `src/options_simulator/analysis/hedge_comparison.py`

**Real-time regime features:**
- Real-time regime classification using actual VIX levels
- VIX percentile analysis with historical context
- Term structure monitoring (VIX vs VIX3M, VIX6M)
- Dynamic regime transition detection

#### 4.2 Comprehensive Testing
**New files to create:**
- `tests/integration/test_real_data_integration.py`
- `tests/mocks/mock_data_generators.py`
- `tests/unit/test_market_data_service.py`

**Testing coverage:**
- Unit tests with mock API responses
- Integration tests for CLI with real/mock data modes
- Error scenario testing (API failures, network issues)
- Performance benchmarks for data fetching

## Technical Architecture

### New Directory Structure
```
src/options_simulator/
├── services/
│   ├── __init__.py
│   ├── market_data_service.py
│   └── service_factory.py
├── data/
│   ├── cache.py
│   └── providers.py (modified)
├── exceptions.py
└── config.py (modified)

tests/
├── integration/
│   └── test_real_data_integration.py
├── mocks/
│   └── mock_data_generators.py
└── unit/
    └── test_market_data_service.py
```

### Data Sources Strategy
1. **Primary**: Yahoo Finance (^VIX, ^TNX, ^IRX, SPY) - Free, reliable, no API key needed
2. **Secondary**: Alpha Vantage (existing API key support) - Premium features, better rate limits
3. **Future**: FRED API for Treasury data - Government source, highly reliable

### Key Technical Decisions

#### 1. Service Layer Pattern
- Separate CLI logic from business logic
- Dependency injection for clean testing
- Interface-based design for provider swapping

#### 2. Async-First Architecture
- Non-blocking data fetching for better UX
- Rich progress indicators during data loading
- Concurrent requests where possible

#### 3. Intelligent Caching
- In-memory cache for real-time data (5-min TTL)
- File-based cache for historical data (daily updates)
- Cache invalidation on stale data detection

#### 4. Error Resilience
- Circuit breaker for failed API calls
- Exponential backoff for rate limiting
- Graceful fallback to mock data with user notification

## Success Metrics

### Functional Requirements
- [ ] Eliminate all hardcoded market values (VIX=22.5, SPY=$420, rate=5%)
- [ ] Real volatility regime classification using live VIX data
- [ ] Historical backtesting against actual crisis periods (2020, 2018, 2008)
- [ ] Comprehensive error handling with graceful fallbacks

### Performance Requirements
- [ ] Sub-second response times with cached data
- [ ] <5 second cold start for fresh data fetches
- [ ] 99%+ uptime with robust fallback mechanisms
- [ ] Memory usage <100MB for typical analysis

### Quality Requirements
- [ ] 90%+ test coverage for new components
- [ ] Zero breaking changes to existing CLI interface
- [ ] Clear user feedback on data source and quality
- [ ] Professional logging for troubleshooting

## Risk Mitigation

### API Dependencies
- **Risk**: Yahoo Finance API changes or rate limiting
- **Mitigation**: Multi-provider fallback, graceful degradation to mock data

### Data Quality
- **Risk**: Stale or incorrect market data
- **Mitigation**: Cross-validation between sources, staleness detection, outlier filtering

### Performance
- **Risk**: Slow API responses impacting CLI UX
- **Mitigation**: Intelligent caching, async operations, progress indicators

### Cost Management
- **Risk**: Unexpected API costs for premium providers
- **Mitigation**: Usage monitoring, rate limiting, configurable provider priority

## Implementation Timeline

### Week 1-2: Foundation
- Extend data providers with VIX/Treasury methods
- Create service layer architecture
- Replace basic mock functions with real data

### Week 3: Historical Integration
- Implement real historical data fetching
- Add crisis period analysis
- Enhanced configuration management

### Week 4: CLI Polish
- Add new command-line options
- Robust error handling and user feedback
- Comprehensive logging

### Week 5-6: Advanced Features
- Real-time volatility regime analysis
- Comprehensive testing suite
- Performance optimization and monitoring

## Next Steps
1. Create context session file for tracking progress
2. Implement Phase 1: Core data infrastructure
3. Test with real market data and validate accuracy
4. Iterate based on performance and user feedback

## Dependencies
- Existing: `yfinance`, `requests`, `pandas`, `numpy`
- New: `aiohttp` for async requests, `redis` for advanced caching (optional)
- Testing: `pytest-asyncio`, `responses` for API mocking

This plan transforms the hedge-compare tool into an institutional-grade system that professional portfolio managers can rely on for real capital allocation decisions.