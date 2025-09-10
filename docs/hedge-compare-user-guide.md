# Hedge Compare User Guide
## A Complete Guide to SPX Tail Hedging Strategy Analysis

---

## Table of Contents
1. [Quick Start Guide (5 minutes)](#quick-start-guide)
2. [Understanding Tail Hedging (15 minutes)](#understanding-tail-hedging)
3. [Tool Output Explained (20 minutes)](#tool-output-explained)
4. [Strategy Selection Framework (15 minutes)](#strategy-selection-framework)
5. [Case Studies & Examples (20 minutes)](#case-studies--examples)
6. [Advanced Topics (30 minutes)](#advanced-topics)

---

## Quick Start Guide

### What This Tool Does
The `hedge-compare` command helps you choose the best **portfolio insurance strategy** using SPX put options. Think of it like comparing different car insurance policies - you want the best protection at the right price.

### Basic Command
```bash
options-sim hedge-compare --portfolio-value 100000 --timeframes "3M,6M"
```

### Quick Decision Framework
**Choose your strategy based on your situation:**

| Your Profile | Recommended Strategy | Why |
|-------------|---------------------|-----|
| **Conservative Investor** (age 50+) | 6-month puts, 15% OTM | Lower annual cost, stable protection |
| **Moderate Risk Tolerance** | 3-month puts, 15% OTM | Balanced cost vs responsiveness |
| **Aggressive/Young Investor** | 2-3 month puts, 18% OTM | More responsive, higher risk tolerance |

### What to Look For in Results
1. **Annual Cost**: Should be 2-5% of your portfolio value
2. **Protection Ratio**: Aim for 3x or higher (you get $3+ back for every $1 spent during crashes)
3. **Recommendation**: The tool will suggest the best strategy for your situation

---

## Understanding Tail Hedging

### The Insurance Analogy
Tail hedging is like **catastrophic insurance for your portfolio**:

- **Home Insurance**: Protects against fire, flood, theft
- **Tail Hedging**: Protects against market crashes, black swan events

Just like you pay annual premiums for home insurance, you pay annual premiums (2-5% of portfolio) for market crash protection.

### Why Traditional Diversification Isn't Enough

**The Problem**: During major crashes, everything falls together
- **2008 Financial Crisis**: Stocks, bonds, real estate all declined
- **March 2020 COVID**: Even "safe" assets dropped 20-30%
- **Correlations Break Down**: Your diversified portfolio still loses 30-50%

**The Solution**: SPX Put Options
- **Negative Correlation**: When markets crash, put options skyrocket
- **Asymmetric Payoff**: Limited downside (premium paid), unlimited upside
- **Crisis Alpha**: Returns of 500-2000% during major market stress

### Historical Performance Examples

| Crisis Event | Market Decline | Typical Put Option Return |
|-------------|----------------|-------------------------|
| **March 2020 COVID** | -34% in 23 days | +1,500-2,000% |
| **2008 Financial Crisis** | -57% over 18 months | +800-1,200% |
| **August 2015 Flash Crash** | -12% in 4 days | +400-600% |

### The Three Key Strategy Types

#### 1. **2-Month Puts (Short-Term Protection)**
- **Pros**: Highly responsive to market moves, lower time decay per day
- **Cons**: Higher annual cost (more frequent rolling), more management required
- **Best For**: Active investors, high conviction about timing

#### 2. **3-Month Puts (Balanced Approach)**
- **Pros**: Good balance of cost and responsiveness
- **Cons**: Moderate complexity in management
- **Best For**: Most investors seeking systematic protection

#### 3. **6-Month Puts (Long-Term Protection)**
- **Pros**: Lower annual cost, less management, stable protection
- **Cons**: Less responsive to quick market moves, higher time decay per day
- **Best For**: Conservative investors, set-and-forget approach

---

## Tool Output Explained

When you run the hedge-compare command, you'll see several key metrics. Here's what each means in plain English:

### Core Strategy Information

#### **Strategy ID** (e.g., "3M_15%_OTM")
- **What it means**: Strategy identifier showing expiration time and how far out-of-the-money
- **Example**: "6M_15%_OTM" = 6-month expiration, 15% out-of-the-money puts
- **Why it matters**: Helps you track and compare different approaches

### Cost Analysis Section

#### **Annual Cost** (e.g., $3,500)
- **What it means**: Total dollar amount you pay per year for this insurance
- **Think of it as**: Your annual insurance premium
- **Target Range**: 2-5% of your total portfolio value
- **Example**: $3,500 annual cost on $100,000 portfolio = 3.5% premium

#### **Cost Percentage** (e.g., 3.5%)
- **What it means**: Annual cost as percentage of your portfolio
- **Why it's important**: Easier to compare across different portfolio sizes
- **Rule of thumb**: 
  - Under 3%: Very cost-efficient
  - 3-5%: Reasonable range
  - Over 5%: Expensive (may not be worth it)

### Protection Analysis Section

#### **Protection Ratio** (e.g., 4.2x)
- **What it means**: How many times your annual premium you expect to get back during major crashes
- **Insurance analogy**: If you pay $1,000/year, you get $4,200 back during a crash
- **Target**: Aim for 3x or higher
- **Why it matters**: Measures effectiveness of your crash protection

#### **Jump Risk Premium** (e.g., +0.15 or +15%)
- **What it means**: Extra protection you get from tail risk models vs standard pricing
- **Simple explanation**: How much extra crash protection this strategy provides
- **Positive numbers**: Good (more crash protection than normal volatility suggests)
- **Negative numbers**: May be overpriced in current market conditions

### Risk Sensitivity Analysis (The Greeks)

#### **Delta** (e.g., -0.08)
- **What it means**: How much your put option price changes when SPX moves $1
- **Example**: Delta of -0.08 means +$0.08 in option value for every $1 SPX drops
- **Why it matters**: Shows sensitivity to market moves
- **For tail hedging**: More negative delta = more responsive protection

#### **Gamma** (e.g., 0.003)
- **What it means**: How much your delta changes as the market moves
- **Think of it as**: "Acceleration" of your protection
- **Higher gamma**: Better for capturing large, sudden moves
- **For tail hedging**: Higher gamma = better black swan protection

#### **Theta** (e.g., -$6.50)
- **What it means**: How much value your options lose per day due to time passage
- **Think of it as**: Daily "rent" you pay for protection
- **Example**: Theta of -$6.50 means you lose $6.50 per day in option value
- **For comparison**: Lower theta (less negative) = less daily cost

#### **Vega** (e.g., 25.4)
- **What it means**: How much your option value changes when volatility changes by 1%
- **Why it matters**: Volatility spikes during crashes, benefiting your puts
- **Higher vega**: More benefit when markets get scared (volatility rises)
- **For tail hedging**: Higher vega = better crisis protection

### Reading the Recommendation Section

The tool provides **clear guidance** based on your situation:

```
RECOMMENDATION: 6M Strategy (★★★★★)
- Best cost efficiency for conservative investors
- Provides 85% crash protection at 3.5% annual cost
- Lower management complexity
- Suitable for long-term protection approach
```

**Star Ratings Explained**:
- ★★★★★: Excellent choice for your profile
- ★★★★☆: Good choice with minor tradeoffs
- ★★★☆☆: Acceptable but not optimal
- ★★☆☆☆: Poor choice for your situation
- ★☆☆☆☆: Avoid this strategy

---

## Strategy Selection Framework

### Step 1: Determine Your Risk Profile

#### **Conservative Investor Profile**
- **Age**: Typically 50+ or nearing retirement
- **Risk Tolerance**: Low to moderate
- **Investment Horizon**: 5-15 years
- **Primary Goal**: Capital preservation
- **Recommended Strategy**: 6-month puts, 15% OTM, 3-4% allocation

#### **Moderate Risk Profile**
- **Age**: Typically 35-50
- **Risk Tolerance**: Moderate
- **Investment Horizon**: 10-25 years
- **Primary Goal**: Growth with protection
- **Recommended Strategy**: 3-month puts, 15% OTM, 3-4% allocation

#### **Aggressive Profile**
- **Age**: Typically under 40
- **Risk Tolerance**: High
- **Investment Horizon**: 20+ years
- **Primary Goal**: Maximum growth, tactical protection
- **Recommended Strategy**: 2-3 month puts, 18% OTM, 2-3% allocation

### Step 2: Consider Market Environment

#### **Low Volatility Environment (VIX < 20)**
- **Characteristics**: Calm markets, steady growth
- **Strategy Adjustment**: Consider longer expirations (6M), lower allocation (2-3%)
- **Rationale**: Protection is cheap, lock in longer-term coverage

#### **Moderate Volatility Environment (VIX 20-30)**
- **Characteristics**: Normal market stress
- **Strategy Adjustment**: Standard approach (3M), normal allocation (3-4%)
- **Rationale**: Balanced cost and protection

#### **High Volatility Environment (VIX > 30)**
- **Characteristics**: Crisis or elevated stress
- **Strategy Adjustment**: Shorter expirations (2-3M), higher allocation (4-5%)
- **Rationale**: More responsive protection when markets are unstable

### Step 3: Portfolio Integration Guidelines

#### **Allocation Recommendations**
- **Minimum Effective**: 2% of portfolio
- **Standard Range**: 3-5% of portfolio  
- **Maximum Recommended**: 5% of portfolio
- **Why these limits**: Below 2% provides insufficient protection; above 5% significantly drags returns

#### **Integration with Other Strategies**
- **Replace cash allocation**: Use tail hedging instead of holding 5-10% cash
- **Complement bond allocation**: Reduce bond allocation by 2-3%, add tail hedging
- **Don't double up**: Avoid if you already have significant defensive positioning

---

## Case Studies & Examples

### Case Study 1: Conservative Pre-Retiree (Sarah, Age 58)

**Portfolio**: $800,000 total value
**Goal**: Protect retirement savings from major market crash
**Risk Tolerance**: Low

**Analysis Using Hedge-Compare Tool**:
```bash
options-sim hedge-compare --portfolio-value 800000 --timeframes "6M,12M" --otm-percentages "0.12,0.15"
```

**Results Summary**:
| Strategy | Annual Cost | Cost % | Protection Ratio | Recommendation |
|----------|-------------|--------|------------------|----------------|
| 6M, 15% OTM | $28,000 | 3.5% | 4.2x | ★★★★★ |
| 12M, 15% OTM | $22,000 | 2.8% | 3.8x | ★★★★☆ |

**Decision**: Choose 6M strategy
- **Rationale**: Best balance of cost and protection
- **Implementation**: $28,000 annual budget for put protection
- **Expected outcome**: $118,000 return during major market crash

**Sarah's Outcome During COVID Crash (Hypothetical)**:
- **Portfolio without hedging**: -$272,000 (-34%)
- **Put option gains**: +$118,000 
- **Net portfolio loss**: -$154,000 (-19.3%)
- **Protection effectiveness**: Reduced crash impact by 43%

### Case Study 2: Moderate Risk Investor (David, Age 42)

**Portfolio**: $300,000 total value
**Goal**: Growth with downside protection
**Risk Tolerance**: Moderate

**Analysis**:
```bash
options-sim hedge-compare --portfolio-value 300000 --timeframes "3M,6M" --otm-percentages "0.15,0.18"
```

**Results**:
| Strategy | Annual Cost | Cost % | Protection Ratio | Recommendation |
|----------|-------------|--------|------------------|----------------|
| 3M, 15% OTM | $12,000 | 4.0% | 5.1x | ★★★★★ |
| 6M, 15% OTM | $9,500 | 3.2% | 4.2x | ★★★★☆ |

**Decision**: Choose 3M strategy
- **Rationale**: Higher protection ratio worth the extra cost at his age
- **Implementation**: Roll puts every 3 months, $12,000 annual budget
- **Expected outcome**: $61,200 return during major crashes

### Case Study 3: High Net Worth Family Office ($5M Portfolio)

**Portfolio**: $5,000,000 total value
**Goal**: Institutional-grade tail risk management
**Risk Tolerance**: Sophisticated, moderate

**Analysis**:
```bash
options-sim hedge-compare --portfolio-value 5000000 --timeframes "2M,3M,6M" --scenario-analysis --jump-diffusion-pricing
```

**Hybrid Strategy Recommendation**:
- **70% allocation**: 3M puts (primary protection)
- **30% allocation**: 6M puts (cost efficiency)
- **Total cost**: $162,500 annually (3.25%)
- **Expected protection**: 4.8x return during stress events

**Advanced Features Used**:
- **Scenario analysis**: Historical backtesting against 2008, 2020 crises
- **Jump-diffusion pricing**: More accurate tail risk modeling
- **Dynamic rebalancing**: Quarterly review and adjustment

---

## Advanced Topics

### Understanding Volatility Regimes

#### **What Are Volatility Regimes?**
Market conditions that affect option pricing and strategy effectiveness:

1. **Low Volatility (VIX < 15)**
   - **Market state**: Calm, steady growth
   - **Option pricing**: Cheap protection
   - **Strategy impact**: Great time to initiate or increase hedging

2. **Normal Volatility (VIX 15-25)**
   - **Market state**: Normal fluctuations
   - **Option pricing**: Fair value
   - **Strategy impact**: Standard hedging approaches work well

3. **High Volatility (VIX 25-40)**
   - **Market state**: Stressed markets
   - **Option pricing**: Expensive but necessary
   - **Strategy impact**: Focus on responsive shorter-term protection

4. **Crisis Volatility (VIX > 40)**
   - **Market state**: Crisis conditions
   - **Option pricing**: Very expensive
   - **Strategy impact**: Existing puts paying off, consider taking profits

### Dynamic Exit Strategies

#### **When to Take Profits**
Unlike buy-and-hold investing, tail hedging sometimes requires profit-taking:

**Profit-Taking Triggers**:
1. **2x gains**: Take 25% profits, let rest run
2. **5x gains**: Take 50% profits during major stress
3. **10x+ gains**: Take 75% profits, maintain core protection

**Example - March 2020**:
- **Strategy**: Hold 6M puts purchased in January 2020
- **March 15**: Puts up 500%, trigger partial profit-taking
- **March 23**: Puts up 1200%, take majority profits
- **Reinvestment**: Buy new protection at lower cost basis

### Advanced Greeks Analysis

#### **Gamma vs Theta Trade-off**
- **High Gamma strategies**: Better for black swan events, higher daily cost
- **Low Gamma strategies**: More cost-efficient, less responsive to shocks
- **Optimal balance**: Depends on your crash prediction confidence

#### **Vega Sensitivity**
- **High Vega**: Benefits more from volatility spikes
- **Low Vega**: Less sensitive to volatility changes
- **Crisis benefit**: Volatility typically doubles during crashes

### Jump-Diffusion Pricing

#### **Why It Matters**
Standard Black-Scholes assumes smooth price movements, but markets can "jump":

- **Normal model**: Gradual 20% decline over 6 months
- **Jump model**: Sudden 10% gap down followed by normal movements
- **Tail hedging**: Jump models better capture protection value

#### **Practical Impact**
- **Jump risk premium**: 10-20% higher option values
- **Better protection**: More accurate crisis scenario modeling
- **Cost justification**: Explains why tail hedging premiums are worth paying

### Portfolio Integration Strategies

#### **Strategic Asset Allocation Integration**
Traditional 60/40 portfolio modification:
- **Original**: 60% stocks, 40% bonds
- **With tail hedging**: 60% stocks, 35% bonds, 5% put protection
- **Expected outcome**: Similar returns, significantly reduced tail risk

#### **Dynamic Hedging**
Advanced approach for sophisticated investors:
- **Increase hedging**: When markets are expensive (high P/E ratios)
- **Decrease hedging**: When markets are cheap (low P/E ratios)
- **Market timing**: Requires active management and market views

#### **Tax Considerations**
- **Short-term capital gains**: Put profits taxed at ordinary income rates
- **Tax loss harvesting**: Can offset gains with portfolio rebalancing
- **Tax-advantaged accounts**: Consider holding hedges in IRAs/401ks

### Common Mistakes to Avoid

#### **1. Over-Hedging (Allocation > 5%)**
- **Problem**: Significantly drags long-term returns
- **Solution**: Stick to 2-5% allocation range

#### **2. Market Timing Attempts**
- **Problem**: Trying to predict when crashes will happen
- **Solution**: Systematic, consistent approach regardless of market views

#### **3. Selling During Payoffs**
- **Problem**: Panic-selling puts when they're paying off during crashes
- **Solution**: Predetermined exit strategy and discipline

#### **4. Wrong Strike Selection**
- **Problem**: Too far OTM (cheap but ineffective) or too close to money (expensive)
- **Solution**: Stick to 10-20% OTM range for optimal cost/protection balance

#### **5. Tracking Hedge Performance Separately**
- **Problem**: Getting frustrated when puts expire worthless
- **Solution**: Evaluate total portfolio performance, not hedge performance alone

---

## Conclusion

Tail hedging with SPX puts is a sophisticated portfolio protection strategy that requires understanding but provides significant crisis protection. The hedge-compare tool simplifies the complex analysis needed to choose optimal strategies for your situation.

**Key Takeaways**:
1. **Think insurance, not investment**: Pay premiums for protection
2. **Cost matters**: Keep annual cost between 2-5% of portfolio
3. **Protection effectiveness**: Target 3x+ protection ratios
4. **Match strategy to profile**: Conservative investors prefer longer expirations
5. **Stay disciplined**: Systematic approach beats market timing

**Next Steps**:
1. Determine your risk profile and target allocation
2. Run the hedge-compare tool with your parameters
3. Implement the recommended strategy
4. Review and adjust quarterly based on market conditions

For technical implementation details, see the [Technical Implementation Guide](spx-hedging-comparison-implementation.md) and [CSV Export Guide](hedge-comparison-export-guide.md).