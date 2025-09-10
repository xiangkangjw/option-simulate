# Hedge Comparison Export Guide
## Understanding Your CSV Results

This guide explains the CSV export from the `options-sim hedge-compare` command in simple terms. If you're new to tail hedging, start with the [Hedge Compare User Guide](hedge-compare-user-guide.md) first.

**Quick Summary**: The CSV contains all the data you need to compare different put option strategies for protecting your portfolio during market crashes.

## CSV Export Fields

When you export results using `--export-format csv`, you get a spreadsheet with all the data needed to analyze your hedging strategies. Here's what each column means:

> **💡 Pro Tip**: Open the CSV in Excel or Google Sheets for easier analysis. You can sort by cost, protection ratio, or any other field to find your optimal strategy.

### 📋 Strategy Identification

**`strategy_id`** - Your Strategy Name
- **What it is**: A simple code that identifies each hedging approach
- **Format**: `{months}M_{percentage}%_OTM`
- **Examples**: 
  - "3M_15%_OTM" = 3-month expiration, 15% out-of-the-money puts
  - "6M_20%_OTM" = 6-month expiration, 20% out-of-the-money puts
- **Why it matters**: Helps you track which strategy is which when comparing results

### 💰 Cost Analysis - What You Pay

**`annual_cost`** - Your Annual Insurance Premium
- **What it is**: Total dollars you pay per year for this protection
- **Think of it as**: Your annual insurance premium for market crash protection
- **Example**: $10,000 means you pay $10,000 per year to maintain this strategy
- **Calculation**: Includes option premiums, rolling costs, and transaction fees
- **Target range**: Should be 2-5% of your total portfolio value

**`cost_percentage`** - Cost as % of Portfolio
- **What it is**: Annual cost divided by your total portfolio value
- **Why it's useful**: Makes it easy to compare across different portfolio sizes
- **Example**: 0.035 = 3.5% of your portfolio spent on hedging each year
- **Guidelines**:
  - **Under 3%**: Very cost-efficient ✅
  - **3-5%**: Reasonable range ✅
  - **Over 5%**: Expensive, may not be worth it ⚠️

### 📊 Advanced Pricing Analysis

**`jump_risk_premium`** - Extra Crash Protection
- **What it is**: How much extra protection you get from advanced pricing models
- **Simple explanation**: Measures "black swan bonus" protection beyond normal market volatility
- **Positive numbers**: Good! More crash protection than standard models suggest
- **Negative numbers**: May be overpriced given current market conditions
- **Example**: 0.15 = 15% extra protection value, meaning this strategy is particularly good at protecting against sudden crashes
- **When to pay attention**: If you're specifically worried about sudden, large market drops

### 🛡️ Protection Effectiveness

**`protection_ratio`** - Your Crash Payoff Multiplier
- **What it is**: How many times your annual premium you expect to get back during major crashes
- **Think of it as**: Return on your insurance premium during disasters
- **Example**: 4.0 means if you pay $10,000/year, you get $40,000 back during a major crash
- **Target**: Aim for 3.0 or higher for meaningful protection
- **Guidelines**:
  - **3.0+**: Good protection ✅
  - **2.0-3.0**: Moderate protection ⚠️
  - **Under 2.0**: Weak protection, probably not worth the cost ❌

### 📈 The Greeks - Risk Sensitivities (Advanced)

The Greeks tell you how your options respond to different market changes. Think of them as the "dials" that control your protection:

> **💡 For Beginners**: Focus on Delta and Theta first. These tell you the most about responsiveness and daily cost.

**`delta`** - Market Sensitivity
- **What it measures**: How much your protection value changes when the market moves
- **For puts**: Always negative (good thing - means you profit when market falls)
- **Example**: -0.08 = option gains $0.08 for every $1 drop in SPX
- **Practical meaning**: More negative delta = more responsive protection
- **What to look for**: More negative numbers mean better immediate protection

**`gamma`** - Acceleration Factor  
- **What it measures**: How much your delta changes as the market moves (think "acceleration")
- **Why it matters**: Higher gamma = better protection during large, sudden moves
- **Example**: 0.003 = your delta becomes more negative as market falls (protection gets stronger)
- **For tail hedging**: Higher gamma = better black swan protection
- **What to look for**: Higher positive numbers for better crash protection

**`theta`** - Daily Cost
- **What it measures**: How much value your options lose each day just from time passing
- **Think of it as**: Daily "rent" you pay for owning protection
- **Always negative**: You lose this amount every day the market doesn't crash
- **Example**: -6.50 = you lose $6.50 per day in option value due to time
- **What to look for**: Less negative numbers = lower daily cost

**`vega`** - Fear Factor Sensitivity
- **What it measures**: How much your options gain when market fear (volatility) increases
- **Why it's important**: Markets get volatile during crashes, benefiting your puts
- **Example**: 25.4 = option gains $25.40 for every 1% increase in market volatility
- **For tail hedging**: Higher vega = more benefit when markets panic
- **What to look for**: Higher positive numbers for better crisis protection

## Quick Decision Framework

### The 30-Second Analysis

When you open your CSV file, look for these key patterns:

1. **Find strategies with cost_percentage between 0.02-0.05** (2-5%)
2. **Look for protection_ratio above 3.0**
3. **Choose based on your profile**:
   - **Conservative**: Lowest cost_percentage with decent protection_ratio
   - **Aggressive**: Highest protection_ratio within your cost budget
   - **Balanced**: Best cost_percentage to protection_ratio ratio

### Red Flags to Avoid ⚠️

- **Cost_percentage > 0.05**: Too expensive
- **Protection_ratio < 2.0**: Weak protection
- **Very negative jump_risk_premium**: Overpriced options

---

## Detailed Analysis Guide

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