"""
CLI command for SPX hedging strategy comparison.

This module provides the command-line interface for comparing different
tail hedging strategies with regime-aware analysis and exit optimization.
"""

import click
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from datetime import datetime
import json
import csv
import logging

from ..analysis.hedge_comparison import HedgeComparisonEngine, HedgingStrategy
from ..analysis.volatility_regime import VolatilityRegime
from ..analysis.exit_strategy import ExitTrigger, ExitTriggerType
from ..config import EnhancedHedgingConfig
from ..services.service_factory import ServiceFactory

logger = logging.getLogger(__name__)
console = Console()


@click.command()
@click.option('--portfolio-value', type=int, default=100000, 
              help='Portfolio value to hedge')
@click.option('--timeframes', type=str, default="2M,3M,6M",
              help='Comma-separated expiration periods (e.g., "2M,3M,6M")')
@click.option('--otm-percentages', type=str, default="0.15,0.25,0.30,0.35",
              help='Comma-separated OTM percentages to analyze (Universa range: 0.25-0.35 for crisis protection)')
@click.option('--symbols', type=str, default="SPY",
              help='Underlying symbols (default: SPY)')
@click.option('--volatility-regime', type=click.Choice(['low', 'medium', 'high', 'extreme', 'auto']),
              default='auto', help='Force specific regime analysis')
@click.option('--enable-dynamic-exits/--no-dynamic-exits', default=True,
              help='Enable profit-taking analysis')
@click.option('--exit-triggers', type=str, default="vix_spike,portfolio_protection,profit_target",
              help='Exit trigger types (vix_spike,portfolio_protection,profit_target,time_decay)')
@click.option('--scenario-analysis/--no-scenario-analysis', default=False,
              help='Include historical scenario testing with vol dynamics')
@click.option('--crisis-periods', type=str, default="covid_2020,volmageddon_2018",
              help='Crisis periods to analyze (covid_2020,volmageddon_2018,financial_2008)')
@click.option('--show-regime-greeks/--no-regime-greeks', default=True,
              help='Display regime-adjusted Greeks comparison')
@click.option('--jump-diffusion-pricing/--no-jump-diffusion', default=True,
              help='Use jump-diffusion models for tail events')
@click.option('--export-format', type=click.Choice(['json', 'csv', 'html']),
              help='Export format')
@click.option('--output', type=str, help='Output file path')
@click.option('--hybrid-analysis/--no-hybrid-analysis', default=True,
              help='Show dynamic hybrid strategy recommendations')
@click.option('--stress-test-depth', type=int, default=6,
              help='Historical stress test depth (default: 6 scenarios)')
@click.option('--vix-level', type=float, help='Override current VIX level for testing')
@click.option('--spy-price', type=float, help='Override current SPY price for testing')
@click.option('--use-real-data/--use-mock-data', default=True,
              help='Use real market data (default) or mock data for testing')
@click.option('--data-provider', type=click.Choice(['yahoo', 'alphavantage', 'auto']),
              default='auto', help='Data provider preference')
@click.option('--max-data-age', type=int, default=300,
              help='Maximum data age in seconds (default: 5 minutes)')
def hedge_compare(portfolio_value: int,
                 timeframes: str,
                 otm_percentages: str, 
                 symbols: str,
                 volatility_regime: str,
                 enable_dynamic_exits: bool,
                 exit_triggers: str,
                 scenario_analysis: bool,
                 show_regime_greeks: bool,
                 jump_diffusion_pricing: bool,
                 export_format: Optional[str],
                 output: Optional[str],
                 hybrid_analysis: bool,
                 stress_test_depth: int,
                 vix_level: Optional[float],
                 spy_price: Optional[float],
                 use_real_data: bool,
                 data_provider: str,
                 max_data_age: int,
                 crisis_periods: str):
    """
    Compare SPX put option hedging strategies with regime-aware analysis.
    
    This command provides comprehensive analysis of tail hedging strategies,
    including volatility regime impact, exit strategy optimization, and
    jump-diffusion pricing for accurate black swan risk assessment.
    """
    
    console.print(Panel.fit(
        "[bold blue]SPX Hedging Strategy Comparison[/bold blue]\n"
        "Enhanced with volatility regime analysis and dynamic exit strategies",
        title="🛡️ Tail Hedging Analyzer"
    ))
    
    try:
        # Parse input parameters
        timeframe_list = _parse_timeframes(timeframes)
        otm_list = _parse_otm_percentages(otm_percentages)
        exit_trigger_list = _parse_exit_triggers(exit_triggers)
        
        # Get market data service
        if data_provider == 'auto':
            market_service = ServiceFactory.get_market_data_service()
        else:
            market_service = ServiceFactory.get_market_data_service(
                primary_provider=data_provider,
                fallback_provider='yahoo'
            )
        
        # Get market conditions with real data or overrides
        if use_real_data:
            console.print("🔄 Fetching real-time market data...")
            market_conditions = market_service.get_current_market_conditions(
                symbol="SPY",
                vix_override=vix_level,
                spy_override=spy_price
            )
            
            # Display data source information
            data_source = market_conditions.get('data_source', 'unknown')
            is_real = market_conditions.get('is_real_data', False)
            data_status = "✅ Live Data" if is_real else "⚠️ Override/Fallback"
            console.print(f"📡 Data Source: {data_source} ({data_status})")
        else:
            console.print("🎭 Using mock market data for testing...")
            market_conditions = _create_market_conditions(vix_level, spy_price)
        
        # Initialize enhanced configuration
        config = EnhancedHedgingConfig()
        
        # Create comparison engine
        engine = HedgeComparisonEngine(config)
        
        console.print(f"📊 Analyzing {len(timeframe_list)} timeframes × {len(otm_list)} OTM levels")
        console.print(f"💼 Portfolio Value: ${portfolio_value:,}")
        console.print(f"📈 Current Market: VIX {market_conditions['vix']:.1f}, SPY ${market_conditions['spy_price']:.2f}")
        
        # Show additional market information for real data
        if use_real_data:
            regime = market_conditions.get('volatility_regime', 'unknown')
            rate = market_conditions.get('risk_free_rate', 0.05)
            timestamp = market_conditions.get('data_timestamp', '')
            console.print(f"⚡ Volatility Regime: {regime.upper()}")
            console.print(f"🏦 Risk-Free Rate: {rate:.2%}")
            if timestamp:
                console.print(f"🕐 Data Time: {timestamp[:16]}")
        
        console.print()
        
        # Create strategy combinations
        strategies = []
        for timeframe_months in timeframe_list:
            for otm_pct in otm_list:
                strategy = _create_hedging_strategy(
                    expiration_months=timeframe_months,
                    otm_percentage=otm_pct,
                    enable_dynamic_exits=enable_dynamic_exits,
                    exit_trigger_list=exit_trigger_list,
                    config=config
                )
                strategies.append(strategy)
        
        console.print(f"🔍 Created {len(strategies)} strategy combinations")
        
        # Run comparison analysis
        with console.status("[bold green]Running comprehensive analysis..."):
            comparison_results = engine.compare_strategies(
                strategies=strategies,
                portfolio_value=portfolio_value,
                current_market_conditions=market_conditions,
                historical_data=_get_enhanced_historical_data(
                    market_service, crisis_periods, use_real_data
                ) if scenario_analysis else None
            )
        
        # Display results
        _display_results(
            comparison_results=comparison_results,
            show_regime_greeks=show_regime_greeks,
            jump_diffusion_pricing=jump_diffusion_pricing,
            hybrid_analysis=hybrid_analysis
        )
        
        # Export results if requested
        if export_format and output:
            _export_results(comparison_results, export_format, output)
            console.print(f"✅ Results exported to {output}")
        
        console.print("\n🎯 Analysis completed successfully!")
        
    except Exception as e:
        console.print(f"❌ Error during analysis: {str(e)}", style="red")
        logger.exception("Hedge comparison failed")
        raise click.ClickException(f"Analysis failed: {str(e)}")


def _parse_timeframes(timeframes_str: str) -> List[int]:
    """Parse timeframe string into months."""
    timeframes = []
    for tf in timeframes_str.split(','):
        tf = tf.strip().upper()
        if tf.endswith('M'):
            months = int(tf[:-1])
            timeframes.append(months)
        else:
            try:
                months = int(tf)
                timeframes.append(months)
            except ValueError:
                raise click.BadParameter(f"Invalid timeframe: {tf}")
    
    return sorted(timeframes)


def _parse_otm_percentages(otm_str: str) -> List[float]:
    """Parse OTM percentage string."""
    otm_percentages = []
    for otm in otm_str.split(','):
        otm = otm.strip()
        try:
            if otm.endswith('%'):
                pct = float(otm[:-1]) / 100
            else:
                pct = float(otm)
            otm_percentages.append(pct)
        except ValueError:
            raise click.BadParameter(f"Invalid OTM percentage: {otm}")
    
    return sorted(otm_percentages)


def _parse_exit_triggers(triggers_str: str) -> List[ExitTriggerType]:
    """Parse exit trigger string."""
    trigger_mapping = {
        'vix_spike': ExitTriggerType.VIX_SPIKE,
        'portfolio_protection': ExitTriggerType.PORTFOLIO_PROTECTION,
        'profit_target': ExitTriggerType.PROFIT_TARGET,
        'time_decay': ExitTriggerType.TIME_DECAY,
        'correlation_breakdown': ExitTriggerType.CORRELATION_BREAKDOWN,
        'liquidity_stress': ExitTriggerType.LIQUIDITY_STRESS
    }
    
    triggers = []
    for trigger in triggers_str.split(','):
        trigger = trigger.strip().lower()
        if trigger in trigger_mapping:
            triggers.append(trigger_mapping[trigger])
        else:
            console.print(f"Warning: Unknown exit trigger '{trigger}' ignored", style="yellow")
    
    return triggers


def _create_market_conditions(vix_override: Optional[float] = None,
                            spy_override: Optional[float] = None) -> Dict[str, float]:
    """Create market conditions (fallback mock data for testing)."""
    return {
        'vix': vix_override or 22.5,
        'spy_price': spy_override or 420.0,
        'risk_free_rate': 0.05,
        'average_correlation': 0.6,
        'volume_ratio': 1.0,
        'bid_ask_spread_ratio': 1.2,
        'portfolio_return': 0.0,  # Assume neutral for new analysis
        'volatility_regime': 'medium',  # Default regime
        'data_timestamp': datetime.now().isoformat(),
        'data_source': 'mock_data',
        'is_real_data': False
    }


def _create_hedging_strategy(expiration_months: int,
                           otm_percentage: float,
                           enable_dynamic_exits: bool,
                           exit_trigger_list: List[ExitTriggerType],
                           config: EnhancedHedgingConfig) -> HedgingStrategy:
    """Create a hedging strategy with the specified parameters."""
    
    # Create volatility regime adjustments
    regime_adjustments = {
        'low': 1.0,
        'medium': 1.2,
        'high': 1.5,
        'extreme': 2.0
    }
    
    # Create exit triggers if dynamic exits are enabled
    exit_triggers = []
    if enable_dynamic_exits:
        for trigger_type in exit_trigger_list:
            if trigger_type == ExitTriggerType.VIX_SPIKE:
                exit_triggers.extend([
                    ExitTrigger(ExitTriggerType.VIX_SPIKE, 30, 0.25, priority=2),
                    ExitTrigger(ExitTriggerType.VIX_SPIKE, 45, 0.50, priority=3),
                    ExitTrigger(ExitTriggerType.VIX_SPIKE, 60, 0.75, priority=4),
                ])
            elif trigger_type == ExitTriggerType.PROFIT_TARGET:
                exit_triggers.extend([
                    ExitTrigger(ExitTriggerType.PROFIT_TARGET, 2.0, 0.25, priority=1),
                    ExitTrigger(ExitTriggerType.PROFIT_TARGET, 5.0, 0.50, priority=2),
                    ExitTrigger(ExitTriggerType.PROFIT_TARGET, 10.0, 0.75, priority=3),
                ])
            elif trigger_type == ExitTriggerType.PORTFOLIO_PROTECTION:
                exit_triggers.extend([
                    ExitTrigger(ExitTriggerType.PORTFOLIO_PROTECTION, 0.05, 0.30, priority=2),
                    ExitTrigger(ExitTriggerType.PORTFOLIO_PROTECTION, 0.10, 0.60, priority=3),
                ])
            # Add other trigger types as needed
    
    return HedgingStrategy(
        expiration_months=expiration_months,
        otm_percentage=otm_percentage,
        rolling_threshold_days=config.default_rolling_threshold,
        volatility_regime_adjustments=regime_adjustments,
        exit_triggers=exit_triggers
    )


def _get_enhanced_historical_data(market_service,
                               crisis_periods_str: str,
                               use_real_data: bool) -> pd.DataFrame:
    """Get enhanced historical data with crisis period support."""
    if not use_real_data:
        console.print("📈 Using simulated historical data for scenario analysis")
        return _get_sample_historical_data()
    
    console.print("📊 Fetching real historical data for scenario analysis...")
    
    # Parse crisis periods
    crisis_list = [p.strip() for p in crisis_periods_str.split(',') if p.strip()]
    
    all_data = pd.DataFrame()
    
    for crisis_name in crisis_list:
        try:
            console.print(f"   🔍 Loading {crisis_name} crisis data...")
            crisis_data = market_service.get_crisis_period_data(crisis_name)
            
            if not crisis_data.empty:
                # Add crisis identifier
                crisis_data['crisis'] = crisis_name
                all_data = pd.concat([all_data, crisis_data], ignore_index=False)
                console.print(f"   ✅ Loaded {len(crisis_data)} days from {crisis_name}")
            else:
                console.print(f"   ⚠️  No data available for {crisis_name}")
        
        except Exception as e:
            console.print(f"   ❌ Failed to load {crisis_name}: {e}")
            continue
    
    if all_data.empty:
        console.print("📈 No real crisis data available, using simulated data")
        return _get_sample_historical_data()
    
    # Remove duplicates and sort by date
    all_data = all_data.sort_index().drop_duplicates()
    
    console.print(f"✅ Loaded total of {len(all_data)} historical data points")
    console.print(f"📅 Date range: {all_data.index.min().strftime('%Y-%m-%d')} to {all_data.index.max().strftime('%Y-%m-%d')}")
    
    # Display crisis period statistics
    if 'crisis' in all_data.columns:
        crisis_summary = all_data.groupby('crisis').agg({
            'vix': ['mean', 'max'],
            'spy_return': ['mean', 'std']
        }).round(3)
        console.print("\n📊 Crisis Period Summary:")
        for crisis in crisis_summary.index:
            vix_mean = crisis_summary.loc[crisis, ('vix', 'mean')]
            vix_max = crisis_summary.loc[crisis, ('vix', 'max')]
            ret_mean = crisis_summary.loc[crisis, ('spy_return', 'mean')]
            ret_std = crisis_summary.loc[crisis, ('spy_return', 'std')]
            console.print(f"   {crisis}: VIX avg={vix_mean:.1f} max={vix_max:.1f}, Return avg={ret_mean:.3f}±{ret_std:.3f}")
    
    return all_data


def _get_sample_historical_data() -> pd.DataFrame:
    """Create sample historical data for scenario analysis."""
    # In a real implementation, this would load actual historical data
    dates = pd.date_range('2020-01-01', '2023-12-31', freq='D')
    np.random.seed(42)  # For reproducible results
    
    # Simulate VIX and SPY data with some correlation
    vix_data = np.random.lognormal(mean=np.log(20), sigma=0.6, size=len(dates))
    vix_data = np.clip(vix_data, 10, 100)  # Realistic VIX range
    
    # SPY returns inversely correlated with VIX spikes
    spy_returns = np.random.normal(0.0008, 0.012, size=len(dates))  # Daily returns
    for i in range(1, len(vix_data)):
        if vix_data[i] > 40:  # High VIX
            spy_returns[i] = np.random.normal(-0.02, 0.03)  # Negative returns during stress
    
    return pd.DataFrame({
        'vix': vix_data,
        'spy_return': spy_returns
    }, index=dates)


def _display_results(comparison_results: Dict,
                    show_regime_greeks: bool,
                    jump_diffusion_pricing: bool, 
                    hybrid_analysis: bool):
    """Display comprehensive analysis results with Universa-style clarity."""
    
    # Current regime and conditions
    current_regime = comparison_results.get('current_volatility_regime', 'unknown')
    portfolio_value = comparison_results.get('portfolio_value', 0)
    
    console.print(Panel(
        f"[bold]Current Volatility Regime:[/bold] {current_regime.upper()}\n"
        f"[bold]Portfolio Value:[/bold] ${portfolio_value:,.0f}\n"
        f"[bold]Analysis Date:[/bold] {comparison_results.get('analysis_timestamp', 'N/A')}"
    ))
    
    # PRIMARY RECOMMENDATION - New enhanced display
    _display_primary_recommendation(comparison_results)
    
    # Crisis vs Volatility Protection Comparison - New section
    _display_protection_type_comparison(comparison_results)
    
    # Strategy rankings table
    _display_strategy_rankings(comparison_results)
    
    # Detailed strategy analysis
    if show_regime_greeks:
        _display_greeks_analysis(comparison_results)
    
    # Jump-diffusion insights
    if jump_diffusion_pricing:
        _display_jump_diffusion_insights(comparison_results)
    
    # Hybrid strategy recommendations
    if hybrid_analysis:
        _display_hybrid_recommendations(comparison_results)
    
    # Recommendations and warnings
    _display_recommendations_and_warnings(comparison_results)


def _display_primary_recommendation(comparison_results: Dict):
    """Display the primary recommendation with clear implementation guidance."""
    recommendations = comparison_results.get('recommendations', {})
    primary_rec = recommendations.get('primary_recommendation', {})
    
    if primary_rec:
        # Get strategy analysis for additional details
        strategy_analysis = comparison_results.get('strategy_analysis', {})
        rec_strategy_id = primary_rec.get('strategy_id', '')
        analysis_data = strategy_analysis.get(rec_strategy_id, {})
        performance_metrics = analysis_data.get('performance_metrics', {})
        
        strategy_type = performance_metrics.get('strategy_type', 'unknown')
        crisis_multiplier = performance_metrics.get('crisis_multiplier', 0)
        protection_ratio = performance_metrics.get('protection_ratio', 0)
        annual_cost = performance_metrics.get('annual_cost', 0)
        allocation_pct = performance_metrics.get('allocation_percentage', 0)
        
        # Style the recommendation based on strategy type
        if strategy_type == "crisis_protection":
            title_style = "bold green"
            protection_type = "🛡️ Crisis Protection (True Tail Hedging)"
            expected_returns = f"100x+ returns during black swan events (>30% market drops)"
        elif strategy_type == "volatility_protection":
            title_style = "bold yellow"
            protection_type = "📈 Volatility Protection"
            expected_returns = f"5-10x returns during volatility spikes (VIX >30)"
        else:
            title_style = "bold cyan"
            protection_type = "⚖️ Balanced Protection"
            expected_returns = f"20-50x returns during market stress"
        
        recommendation_text = (
            f"[{title_style}]🎯 PRIMARY RECOMMENDATION[/{title_style}]\n\n"
            f"[bold]Strategy:[/bold] {primary_rec.get('recommended_strategy', 'N/A')}\n"
            f"[bold]Protection Type:[/bold] {protection_type}\n"
            f"[bold]Confidence Score:[/bold] {primary_rec.get('confidence_score', 0):.0%}\n"
            f"[bold]Expected Crisis Returns:[/bold] {crisis_multiplier}x multiplier\n"
            f"[bold]Expected Returns:[/bold] {expected_returns}\n\n"
            f"[bold]💰 COST ANALYSIS[/bold]\n"
            f"• Annual Cost: ${annual_cost:,.0f} ({allocation_pct:.1%} of portfolio)\n"
            f"• Protection Ratio: {protection_ratio:.1f}x (crisis-adjusted)\n\n"
            f"[bold]🎯 WHY THIS STRATEGY TODAY[/bold]\n"
        )
        
        # Add specific advantages
        advantages = primary_rec.get('key_advantages', [])
        for advantage in advantages:
            recommendation_text += f"• {advantage}\n"
            
        console.print(Panel(
            recommendation_text.strip(),
            title="Strategic Recommendation",
            border_style="green" if strategy_type == "crisis_protection" else "yellow"
        ))
        console.print()


def _display_protection_type_comparison(comparison_results: Dict):
    """Display comparison between crisis protection and volatility protection strategies."""
    strategy_analysis = comparison_results.get('strategy_analysis', {})
    
    if not strategy_analysis:
        return
    
    # Categorize strategies by protection type
    crisis_strategies = []
    volatility_strategies = []
    balanced_strategies = []
    
    for strategy_id, analysis in strategy_analysis.items():
        performance = analysis.get('performance_metrics', {})
        strategy_type = performance.get('strategy_type', 'unknown')
        
        if strategy_type == 'crisis_protection':
            crisis_strategies.append((strategy_id, analysis))
        elif strategy_type == 'volatility_protection':
            volatility_strategies.append((strategy_id, analysis))
        else:
            balanced_strategies.append((strategy_id, analysis))
    
    console.print("[bold blue]📊 PROTECTION TYPE COMPARISON[/bold blue]")
    
    # Create comparison table
    protection_table = Table(show_header=True)
    protection_table.add_column("Strategy", style="cyan", min_width=20)
    protection_table.add_column("Type", style="bold", min_width=15)
    protection_table.add_column("Crisis Returns", justify="right", style="green")
    protection_table.add_column("Annual Cost", justify="right")
    protection_table.add_column("Allocation", justify="right")
    
    # Helper function to add strategy rows
    def add_strategy_row(strategy_id, analysis, protection_type_display):
        performance = analysis.get('performance_metrics', {})
        strategy_details = analysis.get('strategy_details', {})
        
        strategy_name = strategy_details.get('name', strategy_id)
        crisis_multiplier = performance.get('crisis_multiplier', 0)
        annual_cost = performance.get('annual_cost', 0)
        allocation_pct = performance.get('allocation_percentage', 0)
        
        protection_table.add_row(
            strategy_name,
            protection_type_display,
            f"{crisis_multiplier}x",
            f"${annual_cost:,.0f}",
            f"{allocation_pct:.1%}"
        )
    
    # Add crisis protection strategies
    for strategy_id, analysis in crisis_strategies:
        add_strategy_row(strategy_id, analysis, "🛡️ Crisis")
    
    # Add balanced strategies
    for strategy_id, analysis in balanced_strategies:
        add_strategy_row(strategy_id, analysis, "⚖️ Balanced")
    
    # Add volatility protection strategies
    for strategy_id, analysis in volatility_strategies:
        add_strategy_row(strategy_id, analysis, "📈 Volatility")
    
    console.print(protection_table)
    
    # Add explanation panel
    explanation = (
        "[bold]PROTECTION TYPE GUIDE[/bold]\n\n"
        "🛡️  [bold]Crisis Protection (25-35% OTM):[/bold] True Universa-style tail hedging\n"
        "   • 100x+ returns during black swan events (>30% market drops)\n"
        "   • Lower annual cost but requires crisis events for payoff\n"
        "   • Best for portfolio insurance against catastrophic losses\n\n"
        "⚖️  [bold]Balanced Protection (20-25% OTM):[/bold] Hybrid approach\n"
        "   • 20-50x returns during moderate to severe market stress\n"
        "   • Moderate cost and broader event coverage\n\n"
        "📈 [bold]Volatility Protection (10-20% OTM):[/bold] Frequent smaller gains\n"
        "   • 5-10x returns during volatility spikes (VIX >30)\n"
        "   • Higher annual cost but more frequent payoffs\n"
        "   • Good for reducing portfolio volatility"
    )
    
    console.print(Panel(
        explanation,
        title="Understanding Protection Types",
        border_style="blue"
    ))
    console.print()


def _display_strategy_rankings(comparison_results: Dict):
    """Display strategy rankings table."""
    rel_comparisons = comparison_results.get('relative_comparisons', {})
    
    if 'cost_efficiency_ranking' in rel_comparisons:
        console.print("\n📊 [bold blue]Strategy Rankings[/bold blue]")
        
        # Cost efficiency table
        cost_table = Table(title="Cost Efficiency Ranking", show_header=True)
        cost_table.add_column("Rank", style="bold")
        cost_table.add_column("Strategy", style="cyan")
        cost_table.add_column("Annual Cost", justify="right")
        cost_table.add_column("% of Portfolio", justify="right")
        
        for item in rel_comparisons['cost_efficiency_ranking']:
            cost_table.add_row(
                str(item['rank']),
                item['strategy_name'],
                f"${item['annual_cost']:,.0f}",
                f"{item['cost_as_percentage']:.2%}"
            )
        
        console.print(cost_table)
        console.print()


def _display_greeks_analysis(comparison_results: Dict):
    """Display regime-adjusted Greeks analysis."""
    console.print("📈 [bold blue]Regime-Adjusted Greeks Analysis[/bold blue]")
    
    strategy_analysis = comparison_results.get('strategy_analysis', {})
    if not strategy_analysis:
        console.print("No Greeks data available")
        return
    
    greeks_table = Table(show_header=True)
    greeks_table.add_column("Strategy", style="cyan")
    greeks_table.add_column("Delta", justify="right")
    greeks_table.add_column("Gamma", justify="right")
    greeks_table.add_column("Theta", justify="right")
    greeks_table.add_column("Vega", justify="right")
    
    for strategy_id, analysis in strategy_analysis.items():
        greeks = analysis.get('greeks_analysis', {})
        if greeks:
            greeks_table.add_row(
                strategy_id,
                f"{greeks.get('delta', 0):.3f}",
                f"{greeks.get('gamma', 0):.4f}",
                f"{greeks.get('theta', 0):.2f}",
                f"{greeks.get('vega', 0):.3f}"
            )
    
    console.print(greeks_table)
    console.print()


def _display_jump_diffusion_insights(comparison_results: Dict):
    """Display jump-diffusion pricing insights."""
    console.print("🎯 [bold blue]Jump-Diffusion Pricing Insights[/bold blue]")
    
    strategy_analysis = comparison_results.get('strategy_analysis', {})
    
    jd_table = Table(show_header=True)
    jd_table.add_column("Strategy", style="cyan")
    jd_table.add_column("JD Price", justify="right")
    jd_table.add_column("BS Price", justify="right")
    jd_table.add_column("Jump Premium", justify="right", style="green")
    
    for strategy_id, analysis in strategy_analysis.items():
        pricing = analysis.get('pricing_analysis', {})
        if pricing:
            jd_table.add_row(
                strategy_id,
                f"${pricing.get('jump_diffusion_price', 0):.2f}",
                f"${pricing.get('black_scholes_price', 0):.2f}",
                f"{pricing.get('jump_risk_premium', 0):.1%}"
            )
    
    console.print(jd_table)
    console.print()


def _display_hybrid_recommendations(comparison_results: Dict):
    """Display hybrid strategy recommendations."""
    recommendations = comparison_results.get('recommendations', {})
    hybrid_suggestion = recommendations.get('hybrid_strategy_suggestion', {})
    
    if hybrid_suggestion and 'error' not in hybrid_suggestion:
        console.print("🔀 [bold blue]Hybrid Strategy Recommendation[/bold blue]")
        
        allocation = hybrid_suggestion.get('hybrid_allocation', {})
        metrics = hybrid_suggestion.get('hybrid_metrics', {})
        
        hybrid_panel = Panel(
            f"[bold]Allocation:[/bold]\n"
            f"• {allocation.get('short_term_strategy', 'N/A')}: {allocation.get('short_term_weight', 0):.0%}\n"
            f"• {allocation.get('long_term_strategy', 'N/A')}: {allocation.get('long_term_weight', 0):.0%}\n\n"
            f"[bold]Expected Performance:[/bold]\n"
            f"• Blended Annual Cost: ${metrics.get('blended_annual_cost', 0):,.0f}\n"
            f"• Blended Protection Ratio: {metrics.get('blended_protection_ratio', 0):.1f}x\n\n"
            f"[bold]Rationale:[/bold] {hybrid_suggestion.get('rationale', 'N/A')}",
            title="Hybrid Strategy",
            border_style="green"
        )
        
        console.print(hybrid_panel)
        console.print()


def _display_recommendations_and_warnings(comparison_results: Dict):
    """Display recommendations and risk warnings."""
    recommendations = comparison_results.get('recommendations', {})
    
    # Primary recommendation
    primary_rec = recommendations.get('primary_recommendation', {})
    if primary_rec:
        console.print("🎯 [bold green]Primary Recommendation[/bold green]")
        rec_panel = Panel(
            f"[bold]Recommended Strategy:[/bold] {primary_rec.get('recommended_strategy', 'N/A')}\n"
            f"[bold]Confidence:[/bold] {primary_rec.get('confidence_score', 0):.0%}\n"
            f"[bold]Key Advantages:[/bold]\n" +
            "\n".join(f"• {adv}" for adv in primary_rec.get('key_advantages', [])),
            border_style="green"
        )
        console.print(rec_panel)
        console.print()
    
    # Risk warnings
    risk_warnings = recommendations.get('risk_warnings', [])
    if risk_warnings:
        console.print("⚠️  [bold red]Risk Warnings[/bold red]")
        for warning in risk_warnings:
            console.print(f"• {warning}", style="yellow")
        console.print()
    
    # Action items
    action_items = recommendations.get('action_items', [])
    if action_items:
        console.print("📋 [bold blue]Recommended Actions[/bold blue]")
        for i, action in enumerate(action_items, 1):
            console.print(f"{i}. {action}")
        console.print()


def _export_results(comparison_results: Dict, export_format: str, output_path: str):
    """Export results to specified format."""
    try:
        if export_format == 'json':
            with open(output_path, 'w') as f:
                json.dump(comparison_results, f, indent=2, default=str)
        
        elif export_format == 'csv':
            # Create a simplified CSV with key metrics
            _export_to_csv(comparison_results, output_path)
        
        elif export_format == 'html':
            # Create an HTML report
            _export_to_html(comparison_results, output_path)
        
    except Exception as e:
        console.print(f"Export failed: {str(e)}", style="red")
        raise


def _export_to_csv(comparison_results: Dict, output_path: str):
    """Export key metrics to CSV format."""
    strategy_analysis = comparison_results.get('strategy_analysis', {})
    
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = [
            'strategy_id', 'annual_cost', 'cost_percentage', 
            'jump_risk_premium', 'protection_ratio', 'delta', 'gamma', 'theta', 'vega'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for strategy_id, analysis in strategy_analysis.items():
            pricing = analysis.get('pricing_analysis', {})
            greeks = analysis.get('greeks_analysis', {})
            performance = analysis.get('performance_metrics', {})
            
            writer.writerow({
                'strategy_id': strategy_id,
                'annual_cost': pricing.get('annual_cost', 0),
                'cost_percentage': pricing.get('cost_as_percentage', 0),
                'jump_risk_premium': pricing.get('jump_risk_premium', 0),
                'protection_ratio': performance.get('protection_ratio', 0),
                'delta': greeks.get('delta', 0),
                'gamma': greeks.get('gamma', 0),
                'theta': greeks.get('theta', 0),
                'vega': greeks.get('vega', 0)
            })


def _export_to_html(comparison_results: Dict, output_path: str):
    """Export results to HTML format."""
    # Create a basic HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SPX Hedging Strategy Comparison</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .warning {{ color: red; font-weight: bold; }}
            .recommendation {{ color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>SPX Hedging Strategy Comparison Report</h1>
        <p>Generated: {comparison_results.get('analysis_timestamp', 'N/A')}</p>
        <p>Portfolio Value: ${comparison_results.get('portfolio_value', 0):,}</p>
        <p>Current Volatility Regime: {comparison_results.get('current_volatility_regime', 'N/A').upper()}</p>
        
        <h2>Strategy Analysis</h2>
        <p>Detailed analysis results available in JSON format for programmatic access.</p>
        
        <h2>Recommendations</h2>
        <div class="recommendation">
            Primary recommendation and analysis details available in the full JSON export.
        </div>
    </body>
    </html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html_content)