# Options Simulator Documentation

Welcome to the comprehensive documentation for the Options Simulator tail hedging tool. This documentation is designed for users with CFA Level 1 financial knowledge and above.

## 📚 Documentation Guide

### For New Users (Start Here)

1. **[Quick Start Guide](hedge-compare-quick-start.md)** ⚡ **(5 minutes)**
   - Get portfolio protection analysis immediately
   - Basic commands and decision rules
   - Essential metrics to focus on

2. **[User Guide](hedge-compare-user-guide.md)** 📖 **(30 minutes)**
   - Complete educational guide to tail hedging
   - Understanding tool output in plain English
   - Case studies and real-world examples

### For Strategy Selection

3. **[Decision Framework](hedge-strategy-decision-framework.md)** 🎯 **(20 minutes)**
   - Systematic approach to choosing strategies
   - Investor profiles and recommendations
   - Market environment adjustments

### For Data Analysis

4. **[CSV Export Guide](hedge-comparison-export-guide.md)** 📊 **(15 minutes)**
   - Understanding all output fields and metrics
   - How to analyze results in Excel/Sheets
   - Red flags and quality indicators

### For Technical Implementation

5. **[Technical Implementation](spx-hedging-comparison-implementation.md)** ⚙️ **(60 minutes)**
   - Mathematical models and algorithms
   - Advanced features and configuration
   - Developer documentation

## 🎯 Quick Navigation by Use Case

### "I want to start tail hedging immediately"
→ Start with [Quick Start Guide](hedge-compare-quick-start.md)

### "I want to understand tail hedging concepts"
→ Read the [User Guide](hedge-compare-user-guide.md) Introduction sections

### "I need to choose between 3M and 6M puts"
→ Use the [Decision Framework](hedge-strategy-decision-framework.md)

### "I want to analyze the CSV export data"
→ Follow the [CSV Export Guide](hedge-comparison-export-guide.md)

### "I need technical details for implementation"
→ Review [Technical Implementation](spx-hedging-comparison-implementation.md)

## 📊 Tool Commands Quick Reference

### Basic Analysis
```bash
# Quick comparison for most users
options-sim hedge-compare --portfolio-value 100000 --timeframes "3M,6M"
```

### Comprehensive Analysis
```bash
# Full feature analysis with export
options-sim hedge-compare \
  --portfolio-value 100000 \
  --timeframes "2M,3M,6M" \
  --otm-percentages "0.12,0.15,0.18" \
  --scenario-analysis \
  --export-format csv
```

### Advanced Features
```bash
# Institutional-grade analysis
options-sim hedge-compare \
  --portfolio-value 1000000 \
  --timeframes "2M,3M,6M,12M" \
  --volatility-regime auto \
  --enable-dynamic-exits \
  --jump-diffusion-pricing \
  --scenario-analysis
```

## 🎓 Educational Progression

### Level 1: Basic User (CFA L1 knowledge)
1. Quick Start → User Guide (Sections 1-3) → Decision Framework
2. **Time Investment**: 45 minutes
3. **Outcome**: Can select and implement appropriate tail hedging strategy

### Level 2: Advanced User (CFA L2+ or professional)
1. All Level 1 content → CSV Export Guide → User Guide (Advanced sections)
2. **Time Investment**: 90 minutes  
3. **Outcome**: Can analyze strategies in detail and optimize for specific situations

### Level 3: Technical Implementation (Developers/Quants)
1. All previous content → Technical Implementation → Advanced configuration
2. **Time Investment**: 3+ hours
3. **Outcome**: Can customize, extend, and integrate the tool

## 📈 Key Concepts Summary

### Tail Hedging Fundamentals
- **Purpose**: Portfolio insurance against market crashes
- **Method**: Systematic purchase of out-of-the-money SPX puts
- **Cost**: 2-5% of portfolio value annually
- **Benefit**: 3-10x returns during major market stress

### Strategy Types
- **2-3 Month Puts**: High responsiveness, higher cost, active management
- **6 Month Puts**: Cost efficiency, lower maintenance, stable protection
- **Hybrid Approaches**: Combination strategies for sophisticated investors

### Key Metrics
- **Annual Cost**: Total yearly premium expense
- **Protection Ratio**: Expected return multiplier during crashes
- **Greeks**: Risk sensitivities (Delta, Gamma, Theta, Vega)
- **Jump Risk Premium**: Extra tail protection beyond normal volatility models

## 🛠️ Tool Features

### Core Analysis
- Strategy comparison across multiple timeframes
- Cost-benefit analysis with protection ratios
- Greeks calculations for risk sensitivity
- Market environment adjustments

### Advanced Features
- Historical scenario backtesting
- Jump-diffusion pricing models
- Volatility regime analysis
- Dynamic exit strategy modeling
- Comprehensive CSV exports

### User Experience
- Rich terminal interface with clear recommendations
- Progressive disclosure for different skill levels
- Practical decision frameworks
- Real-world case studies and examples

## 🤝 Support & Contributing

### Getting Help
- **Command Help**: `options-sim hedge-compare --help`
- **Documentation Issues**: Review this documentation hierarchy
- **Technical Issues**: Check Technical Implementation guide

### Feedback
- Documentation feedback welcome for clarity and accessibility
- Feature requests should include use case and investor profile
- Bug reports should include command used and expected vs actual output

---

## 📋 Document Status

| Document | Target Audience | Last Updated | Status |
|----------|----------------|--------------|---------|
| Quick Start | All users | Current | ✅ Complete |
| User Guide | CFA L1+ | Current | ✅ Complete |
| Decision Framework | Investors | Current | ✅ Complete |
| CSV Export Guide | Data analysts | Current | ✅ Complete |
| Technical Implementation | Developers | Current | ✅ Complete |

---

**Note**: This documentation assumes familiarity with basic portfolio theory, options fundamentals, and risk management concepts typically covered in CFA Level 1 curriculum. For more basic financial education, consider reviewing CFA Institute materials or similar foundational resources before using advanced tail hedging strategies.