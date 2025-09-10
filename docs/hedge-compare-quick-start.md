# Hedge Compare Quick Start
## Get Portfolio Protection Analysis in 5 Minutes

---

## What This Tool Does

**The hedge-compare tool helps you choose the best "portfolio insurance" strategy using SPX put options.**

Think of it like comparing car insurance policies - you want the best crash protection at the right price.

---

## Step 1: Basic Command (30 seconds)

```bash
options-sim hedge-compare --portfolio-value YOUR_PORTFOLIO_VALUE --timeframes "3M,6M"
```

**Replace YOUR_PORTFOLIO_VALUE with your actual portfolio size:**
- $100,000 portfolio: `--portfolio-value 100000`
- $500,000 portfolio: `--portfolio-value 500000`  
- $1M portfolio: `--portfolio-value 1000000`

**Example:**
```bash
options-sim hedge-compare --portfolio-value 250000 --timeframes "3M,6M"
```

---

## Step 2: Read the Results (2 minutes)

Look for these key numbers in the output:

### 🎯 **Annual Cost**
- **What it means**: How much you pay per year for protection
- **Target**: Should be 2-5% of your portfolio value
- **Example**: $250K portfolio should cost $5K-$12.5K annually

### 🛡️ **Protection Ratio** 
- **What it means**: How much you get back during crashes
- **Target**: Look for 3.0x or higher
- **Example**: 4.0x means $10K premium becomes $40K during major crash

### ⭐ **Recommendation**
- **What it means**: Tool's suggested best strategy for you
- **Look for**: 4-5 star ratings (★★★★★)

---

## Step 3: Quick Decision Rules (1 minute)

### If You're Conservative (Age 50+)
- **Choose**: 6-month strategy with lowest annual cost
- **Target**: 3-4% of portfolio, 3x+ protection ratio

### If You're Moderate Risk (Age 35-50)  
- **Choose**: 3-month strategy for balanced approach
- **Target**: 3-4% of portfolio, 4x+ protection ratio

### If You're Aggressive (Age <35)
- **Choose**: 2-3 month strategy for maximum responsiveness
- **Target**: 2-3% of portfolio, 5x+ protection ratio

---

## Step 4: Advanced Analysis (Optional)

### Export Results for Detailed Analysis
```bash
options-sim hedge-compare --portfolio-value 250000 --timeframes "2M,3M,6M" --export-format csv --output my_hedge_analysis.csv
```

### Include Historical Testing
```bash
options-sim hedge-compare --portfolio-value 250000 --timeframes "3M,6M" --scenario-analysis
```

### Test Multiple Strike Levels
```bash
options-sim hedge-compare --portfolio-value 250000 --timeframes "3M,6M" --otm-percentages "0.12,0.15,0.18"
```

---

## Real Example Walkthrough

**Scenario**: You have a $300,000 portfolio and want protection

**Command:**
```bash
options-sim hedge-compare --portfolio-value 300000 --timeframes "3M,6M"
```

**Sample Results:**
```
Strategy Comparison - $300,000 Portfolio

Strategy        Annual Cost    Cost %    Protection    Recommendation
─────────────────────────────────────────────────────────────────────
3M_15%_OTM      $12,000       4.0%      5.1x          ★★★★★
6M_15%_OTM      $9,500        3.2%      4.2x          ★★★★☆

RECOMMENDATION: 3M Strategy
- Higher protection ratio (5.1x vs 4.2x)
- More responsive to market moves
- Worth extra $2,500 annual cost for better protection
```

**Decision**: Choose 3-month strategy
- **Annual cost**: $12,000 (4% of portfolio - within target range)
- **Expected crash return**: $61,200 (5.1x protection ratio)
- **Why**: Better protection ratio worth the extra cost

---

## When to Use Each Strategy

### 6-Month Puts (Long-term Protection)
✅ **Good for**:
- Conservative investors
- Set-and-forget approach  
- Lower management complexity
- Cost-conscious investors

❌ **Avoid if**:
- You want maximum responsiveness
- You actively monitor markets
- You prefer tactical approaches

### 3-Month Puts (Balanced Approach)  
✅ **Good for**:
- Most investors
- Balanced cost vs performance
- Moderate risk tolerance
- Standard hedging approach

❌ **Avoid if**:
- You want lowest possible cost
- You want maximum responsiveness
- You hate managing investments

### 2-Month Puts (High Responsiveness)
✅ **Good for**:
- Active investors
- Maximum market sensitivity
- Tactical hedging
- High conviction timing

❌ **Avoid if**:
- You want low maintenance
- You're cost-sensitive
- You prefer stable, predictable costs

---

## Red Flags to Avoid

### 🚫 **Don't Choose Strategies With**:
- **Cost > 5% of portfolio**: Too expensive, will hurt long-term returns
- **Protection ratio < 2.0**: Weak protection, not worth the cost
- **Annual cost < 1% of portfolio**: Probably insufficient protection

### 🚫 **Common Mistakes**:
- **Over-hedging**: Using more than 5% of portfolio for hedging
- **Under-hedging**: Using less than 2% (insufficient protection)
- **Market timing**: Turning hedging on/off based on market predictions
- **Profit panic**: Selling puts when they start paying off during crashes

---

## Next Steps

1. **Run the basic command** with your portfolio value
2. **Choose a strategy** based on the recommendations
3. **Implement systematically** - don't try to time the market
4. **Review quarterly** - adjust based on portfolio changes

---

## Need More Detail?

- **Full Guide**: [Hedge Compare User Guide](hedge-compare-user-guide.md) - Complete educational guide (30 minutes)
- **Technical Details**: [CSV Export Guide](hedge-comparison-export-guide.md) - Understanding all the data
- **Implementation**: [Technical Implementation](spx-hedging-comparison-implementation.md) - For developers

---

## Help & Support

**Common Issues**:
- **"Command not found"**: Make sure you've installed the tool with `pip install -e .`
- **"No data available"**: Check your internet connection for market data
- **"Invalid portfolio value"**: Use numbers without commas (e.g., 100000 not 100,000)

**Get help**: Run `options-sim hedge-compare --help` for all available options