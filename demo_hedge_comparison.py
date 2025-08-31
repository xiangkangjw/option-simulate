#!/usr/bin/env python3
"""
Demo script for the enhanced SPX hedge comparison functionality.

This script demonstrates the key capabilities of the enhanced tail hedging
comparison system that addresses volatility regime dynamics and early profit realization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from options_simulator.analysis.hedge_comparison import HedgeComparisonEngine, HedgingStrategy
from options_simulator.analysis.exit_strategy import ExitTrigger, ExitTriggerType
from options_simulator.config import EnhancedHedgingConfig

def main():
    """Demonstrate the enhanced hedge comparison system."""
    print("🛡️  SPX TAIL HEDGING COMPARISON - ENHANCED SYSTEM DEMO")
    print("=" * 80)
    print()
    
    # Initialize enhanced configuration
    config = EnhancedHedgingConfig()
    engine = HedgeComparisonEngine(config)
    
    print("📋 CREATING STRATEGY COMPARISON...")
    print("Comparing 2-month vs 6-month SPX put strategies with regime awareness")
    print()
    
    # Create strategies with enhanced features
    strategies = [
        # Short-term strategy with aggressive exit triggers
        HedgingStrategy(
            expiration_months=2,
            otm_percentage=0.15,
            rolling_threshold_days=21,
            volatility_regime_adjustments={
                'low': 1.0, 'medium': 1.3, 'high': 1.8, 'extreme': 2.5
            },
            exit_triggers=[
                ExitTrigger(ExitTriggerType.VIX_SPIKE, 30, 0.25, priority=2),
                ExitTrigger(ExitTriggerType.PROFIT_TARGET, 3.0, 0.40, priority=3),
                ExitTrigger(ExitTriggerType.PORTFOLIO_PROTECTION, 0.08, 0.50, priority=4),
            ]
        ),
        
        # Long-term strategy with conservative exit triggers  
        HedgingStrategy(
            expiration_months=6,
            otm_percentage=0.15,
            rolling_threshold_days=21,
            volatility_regime_adjustments={
                'low': 1.0, 'medium': 1.2, 'high': 1.4, 'extreme': 1.8
            },
            exit_triggers=[
                ExitTrigger(ExitTriggerType.PROFIT_TARGET, 5.0, 0.30, priority=2),
                ExitTrigger(ExitTriggerType.TIME_DECAY, 0.10, 0.25, priority=1),
            ]
        )
    ]
    
    # Test in different market regimes
    market_scenarios = [
        {
            "name": "Low Volatility Environment",
            "conditions": {
                "vix": 15.0,
                "spy_price": 420.0,
                "risk_free_rate": 0.05,
                "average_correlation": 0.5,
                "volume_ratio": 1.0,
                "bid_ask_spread_ratio": 1.1,
                "portfolio_return": 0.01
            }
        },
        {
            "name": "High Volatility Crisis",
            "conditions": {
                "vix": 45.0,
                "spy_price": 380.0,
                "risk_free_rate": 0.05,
                "average_correlation": 0.85,
                "volume_ratio": 0.6,
                "bid_ask_spread_ratio": 2.2,
                "portfolio_return": -0.12
            }
        }
    ]
    
    for scenario in market_scenarios:
        print(f"🎯 ANALYZING: {scenario['name']}")
        print(f"   VIX: {scenario['conditions']['vix']:.1f}, SPY: ${scenario['conditions']['spy_price']:.2f}")
        print()
        
        # Run comprehensive analysis
        results = engine.compare_strategies(
            strategies=strategies,
            portfolio_value=500000,  # $500k portfolio
            current_market_conditions=scenario['conditions']
        )
        
        # Display key insights
        current_regime = results.get('current_volatility_regime', 'unknown')
        print(f"   📊 Current Regime: {current_regime.upper()}")
        
        # Strategy analysis summary
        strategy_analysis = results.get('strategy_analysis', {})
        
        print("   💰 Cost Analysis:")
        for strategy_id, analysis in strategy_analysis.items():
            annual_cost = analysis['pricing_analysis']['annual_cost']
            cost_pct = analysis['pricing_analysis']['cost_as_percentage']
            jump_premium = analysis['pricing_analysis']['jump_risk_premium']
            
            print(f"      {strategy_id}: ${annual_cost:,.0f} ({cost_pct:.2%}) | Jump Premium: {jump_premium:.1%}")
        
        # Volatility regime impact
        print("   📈 Regime Impact:")
        for strategy_id, analysis in strategy_analysis.items():
            vol_adjustment = analysis['regime_impact_analysis']['volatility_adjustment']
            cost_multiplier = analysis['regime_impact_analysis']['cost_impact_multiplier']
            
            print(f"      {strategy_id}: Vol Adj {vol_adjustment:+.1%} | Cost Impact {cost_multiplier:.2f}x")
        
        # Exit opportunities  
        print("   🚪 Exit Analysis:")
        for strategy_id, analysis in strategy_analysis.items():
            exit_rec = analysis['exit_strategy_analysis']['current_exit_recommendation']
            urgency = exit_rec['urgency_score']
            exit_pct = exit_rec['recommended_exit_percentage']
            
            if exit_pct > 0:
                print(f"      {strategy_id}: EXIT {exit_pct:.0%} (Urgency: {urgency:.1f})")
            else:
                print(f"      {strategy_id}: HOLD (Urgency: {urgency:.1f})")
        
        # Primary recommendation
        primary_rec = results.get('recommendations', {}).get('primary_recommendation', {})
        if primary_rec:
            rec_strategy = primary_rec.get('recommended_strategy', 'N/A')
            confidence = primary_rec.get('confidence_score', 0)
            print(f"   🎯 RECOMMENDATION: {rec_strategy} (Confidence: {confidence:.0%})")
        
        # Risk warnings
        risk_warnings = results.get('recommendations', {}).get('risk_warnings', [])
        if risk_warnings:
            print("   ⚠️  RISK WARNINGS:")
            for warning in risk_warnings[:2]:  # Show top 2
                print(f"      • {warning}")
        
        print()
        print("-" * 80)
        print()
    
    print("🎉 DEMONSTRATION COMPLETED!")
    print()
    print("✅ KEY ENHANCEMENTS DEMONSTRATED:")
    print("   • Volatility regime impact on relative pricing (2M vs 6M)")
    print("   • Dynamic exit strategy optimization during market stress")
    print("   • Jump-diffusion pricing for accurate tail risk assessment") 
    print("   • Regime-aware strategy recommendations")
    print("   • Comprehensive risk warnings and action items")
    print()
    print("📚 This addresses the original gaps in:")
    print("   1. Volatility regime dynamics (2M puts become expensive vs 6M during stress)")
    print("   2. Early profit realization (capturing 5x-20x gains during black swan events)")
    print()
    print("🚀 The system is now ready for institutional-grade tail hedging analysis!")

if __name__ == "__main__":
    main()