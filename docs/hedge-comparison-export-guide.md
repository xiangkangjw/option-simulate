# Hedge Comparison Export Guide

This guide explains the fields in the CSV export from the `options-sim hedge-compare` command.

## CSV Export Fields

When you export hedge comparison results using `--export-format csv`, the CSV file contains the following fields:

### Core Strategy Identification
- **`strategy_id`**: Unique identifier for the strategy (e.g., "3M_15%_OTM", "6M_20%_OTM")
  - Format: `{expiration_months}M_{otm_percentage}%_OTM`
  - Example: "6M_15%_OTM" = 6-month expiration, 15% out-of-the-money puts

### Cost Analysis
- **`annual_cost`**: Total annual cost of the hedging strategy in dollars
  - Calculated based on option premium × contracts needed × rolling frequency
  - Example: $10,000 means the strategy costs $10,000 per year to maintain
  
- **`cost_percentage`**: Annual cost as a percentage of total portfolio value
  - Formula: `annual_cost / portfolio_value`
  - Example: 0.10 = 10% of portfolio value spent on hedging annually

### Pricing Analysis
- **`jump_risk_premium`**: Premium captured by jump-diffusion pricing vs Black-Scholes
  - Represents additional tail risk protection beyond standard Black-Scholes model
  - Positive values indicate jump-diffusion model prices options higher (better tail protection)
  - Example: 0.15 = 15% higher price than Black-Scholes, indicating significant tail risk premium

### Performance Metrics  
- **`protection_ratio`**: Expected return multiplier during stress events
  - Indicates how many times the strategy cost you expect to recover during market crashes
  - Example: 3.0 = expect 3x returns (300% gains) during tail events
  - Higher values indicate more effective portfolio protection

### Greeks (Risk Sensitivities)
The Greeks measure how option prices change with various market factors:

- **`delta`**: Price sensitivity to underlying asset movement
  - Negative for puts (price increases when underlying falls)
  - Example: -0.032 = option price increases $0.032 per $1 decline in SPY
  
- **`gamma`**: Rate of change of delta (convexity measure)
  - Higher gamma provides better convexity during large moves
  - Example: 0.0018 = delta increases by 0.0018 for each $1 move in underlying
  
- **`theta`**: Time decay (daily price erosion)
  - Always negative for long options
  - Example: 5.29 = option loses $5.29 in value per day due to time decay
  
- **`vega`**: Volatility sensitivity
  - Positive for long options (benefit from volatility increases)
  - Example: 14.280 = option price increases $14.28 per 1% increase in implied volatility

## Interpreting the Results

### Cost Efficiency Analysis
- **Lower `annual_cost`** and **`cost_percentage`** = more cost-efficient
- Compare across strategies to find optimal cost-protection balance
- Consider `cost_percentage` < 5% as reasonable for most portfolios

### Protection Effectiveness
- **Higher `protection_ratio`** = better crisis protection
- Look for strategies with `protection_ratio` > 3.0 for meaningful tail protection
- Balance against cost - sometimes lower protection ratios are acceptable for cost savings

### Jump Risk Assessment
- **Positive `jump_risk_premium`** indicates significant tail risk capture
- Values > 0.10 (10%) suggest the strategy is well-suited for black swan protection
- Negative values may indicate overpriced options in current market conditions

### Greeks Optimization
- **Higher `gamma`**: Better for capturing large moves but more expensive
- **Lower `theta`**: Less time decay, better for longer-term protection
- **Higher `vega`**: More sensitive to volatility spikes (good for tail hedging)
- **More negative `delta`**: Higher sensitivity to market declines

## Example Strategy Comparison

```csv
strategy_id,annual_cost,cost_percentage,jump_risk_premium,protection_ratio,delta,gamma,theta,vega
3M_15%_OTM,20000,0.20,-0.139,3.0,-0.032,0.0018,5.29,14.280
6M_15%_OTM,10000,0.10,-0.192,3.0,-0.080,0.0027,6.93,43.908
```

**Analysis:**
- **Cost**: 6M strategy is half the annual cost (10% vs 20% of portfolio)
- **Protection**: Both offer same protection ratio (3.0x returns during stress)
- **Sensitivity**: 6M has higher delta (-0.080 vs -0.032) = more responsive to market moves
- **Time Decay**: 6M has higher theta (6.93 vs 5.29) but spread over longer timeframe
- **Volatility**: 6M much higher vega (43.908 vs 14.280) = better volatility protection

**Recommendation**: 6M strategy offers better cost efficiency and volatility protection.

## Best Practices

### Strategy Selection Guidelines
1. **Cost Constraint**: Keep `cost_percentage` under 5% of portfolio for most investors
2. **Protection Target**: Aim for `protection_ratio` ≥ 3.0 for meaningful tail hedging
3. **Jump Premium**: Positive `jump_risk_premium` indicates good tail risk capture
4. **Greeks Balance**: Higher `vega` and `gamma` with manageable `theta` for tail hedging

### Export Usage
- Use CSV exports for:
  - Backtesting analysis in spreadsheet applications
  - Integration with portfolio management systems
  - Historical comparison tracking over time
  - Custom visualization and reporting

### Data Validation
- Verify `cost_percentage` aligns with your risk budget
- Check `protection_ratio` values are realistic (typically 1.5x to 10x)
- Ensure Greeks values are reasonable for the option characteristics
- Cross-reference with market conditions and volatility regime

## Additional Resources
- See `docs/spx-hedging-comparison-implementation.md` for detailed mathematical models
- Run `options-sim hedge-compare --help` for all available export options
- Use `--scenario-analysis` flag for historical backtesting data in exports