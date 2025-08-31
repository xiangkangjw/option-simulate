"""Main CLI interface for the options simulator."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from tabulate import tabulate
from typing import Dict, Any
import json
from datetime import date

from ..config import StrategyConfig, settings
from ..data.providers import DataProviderFactory, MarketDataManager
from ..strategies.tail_hedging import TailHedgingStrategy


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Options Trading Simulation Tool - Universa-Style Tail Hedging
    
    A CLI tool for simulating tail risk hedging strategies using
    out-of-the-money put options following Universa Investments principles.
    """
    pass

# Import the hedge comparison command
from .hedge_compare import hedge_compare

# Add the hedge comparison command to the CLI group
cli.add_command(hedge_compare)


@cli.command()
@click.option('--portfolio-value', '-p', default=100000, type=float, 
              help='Initial portfolio value (default: $100,000)')
@click.option('--hedge-allocation', '-a', default=0.05, type=float,
              help='Allocation to hedging (default: 5%)')
@click.option('--otm-percentage', '-o', default=0.15, type=float,
              help='Out-of-the-money percentage (default: 15%)')
@click.option('--symbols', '-s', default="SPY,QQQ,IWM", type=str,
              help='Comma-separated list of symbols to hedge (default: SPY,QQQ,IWM)')
@click.option('--provider', '-d', default="yahoo", type=click.Choice(['yahoo', 'alphavantage']),
              help='Data provider (default: yahoo)')
@click.option('--dry-run', is_flag=True, help='Show strategy setup without executing')
def run(portfolio_value, hedge_allocation, otm_percentage, symbols, provider, dry_run):
    """Run the tail hedging strategy."""
    
    # Parse symbols
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    # Create configuration
    config = StrategyConfig(
        portfolio_value=portfolio_value,
        hedge_allocation=hedge_allocation,
        otm_percentage=otm_percentage,
        underlying_symbols=symbol_list
    )
    
    # Display configuration
    display_strategy_config(config)
    
    if dry_run:
        console.print("\n[yellow]Dry run mode - no trades will be executed[/yellow]")
        return
    
    # Initialize data manager and strategy
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing strategy...", total=None)
        
        try:
            data_manager = MarketDataManager(primary_provider=provider)
            strategy = TailHedgingStrategy(config, data_manager)
            
            progress.update(task, description="Fetching market data...")
            
            # Get current market data
            market_data = {}
            for symbol in symbol_list:
                price = data_manager.get_stock_price(symbol)
                if price > 0:
                    market_data[symbol] = price
                    console.print(f"[green]{symbol}:[/green] ${price:.2f}")
                else:
                    console.print(f"[red]Warning: Could not fetch price for {symbol}[/red]")
            
            if not market_data:
                console.print("[red]Error: No market data available[/red]")
                return
            
            progress.update(task, description="Establishing initial positions...")
            
            # Run initial strategy step
            strategy.run_strategy_step(market_data)
            
            progress.update(task, description="Complete!")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    # Display results
    display_strategy_results(strategy)


@cli.command()
@click.option('--symbol', '-s', default="SPY", help='Symbol to analyze (default: SPY)')
@click.option('--otm-percentage', '-o', default=0.15, type=float,
              help='Out-of-the-money percentage (default: 15%)')
@click.option('--provider', '-d', default="yahoo", type=click.Choice(['yahoo', 'alphavantage']),
              help='Data provider (default: yahoo)')
def analyze(symbol, otm_percentage, provider):
    """Analyze options chain for tail hedging opportunities."""
    
    console.print(f"\n[bold]Analyzing tail hedging opportunities for {symbol}[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching data...", total=None)
        
        try:
            data_manager = MarketDataManager(primary_provider=provider)
            
            # Get current price
            current_price = data_manager.get_stock_price(symbol)
            if current_price == 0:
                console.print(f"[red]Error: Could not fetch price for {symbol}[/red]")
                return
            
            console.print(f"Current {symbol} price: [green]${current_price:.2f}[/green]")
            
            progress.update(task, description="Fetching options chain...")
            
            # Get tail hedge candidates
            candidates = data_manager.get_tail_hedge_candidates(symbol, current_price, otm_percentage)
            
            if not candidates:
                console.print("[red]No suitable tail hedging options found[/red]")
                return
            
            progress.update(task, description="Analyzing options...")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    
    # Display options analysis
    display_options_analysis(symbol, current_price, candidates, otm_percentage)


@cli.command()
@click.option('--config-file', '-c', type=click.Path(exists=True),
              help='Load configuration from JSON file')
def backtest(config_file):
    """Run historical backtesting of the strategy."""
    console.print("[yellow]Backtesting functionality coming soon...[/yellow]")
    # TODO: Implement backtesting


@cli.command()
def config():
    """Display current configuration settings."""
    
    config_table = Table(title="Current Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Max Portfolio Allocation", f"{settings.max_portfolio_allocation:.1%}")
    config_table.add_row("Default Rolling Days", str(settings.default_rolling_days))
    config_table.add_row("Default OTM Percentage", f"{settings.default_otm_percentage:.1%}")
    config_table.add_row("Initial Portfolio Value", f"${settings.initial_portfolio_value:,.0f}")
    config_table.add_row("Transaction Cost/Contract", f"${settings.transaction_cost_per_contract:.2f}")
    config_table.add_row("Risk-Free Rate", f"{settings.risk_free_rate:.1%}")
    
    console.print(config_table)
    
    # Show API key status
    api_panel = Panel(
        f"Alpha Vantage: {'✓ Configured' if settings.alpha_vantage_api_key else '✗ Not configured'}\n"
        f"Polygon: {'✓ Configured' if settings.polygon_api_key else '✗ Not configured'}",
        title="API Keys Status"
    )
    console.print(api_panel)


def display_strategy_config(config: StrategyConfig):
    """Display strategy configuration in a formatted table."""
    
    table = Table(title="Tail Hedging Strategy Configuration")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Portfolio Value", f"${config.portfolio_value:,.0f}")
    table.add_row("Hedge Allocation", f"{config.hedge_allocation:.1%}")
    table.add_row("Hedge Capital", f"${config.hedge_capital:,.0f}")
    table.add_row("OTM Percentage", f"{config.otm_percentage:.1%}")
    table.add_row("Rolling Days", str(config.rolling_days))
    table.add_row("Target DTE", str(config.target_dte))
    table.add_row("Underlying Symbols", ", ".join(config.underlying_symbols))
    
    console.print(table)


def display_strategy_results(strategy: TailHedgingStrategy):
    """Display strategy execution results."""
    
    summary = strategy.get_performance_summary()
    
    # Performance summary table
    perf_table = Table(title="Strategy Performance Summary")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="green")
    
    perf_table.add_row("Initial Value", f"${summary['initial_value']:,.0f}")
    perf_table.add_row("Current Value", f"${summary['current_value']:,.0f}")
    perf_table.add_row("Total Return", f"{summary['total_return']:.2%}")
    perf_table.add_row("Hedge Cost", f"{summary['hedge_cost_percentage']:.2%}")
    perf_table.add_row("Options Allocation", f"{summary['options_allocation']:.2%}")
    perf_table.add_row("Number of Trades", str(summary['num_trades']))
    perf_table.add_row("Cash Available", f"${summary['cash']:,.0f}")
    
    console.print(perf_table)
    
    # Current positions
    if summary['current_positions']:
        pos_table = Table(title="Current Positions")
        pos_table.add_column("Symbol", style="cyan")
        pos_table.add_column("Strike", style="white")
        pos_table.add_column("Expiration", style="white")
        pos_table.add_column("Quantity", style="white")
        pos_table.add_column("Value", style="green")
        pos_table.add_column("P&L", style="red")
        pos_table.add_column("DTE", style="yellow")
        
        for pos in summary['current_positions']:
            pnl_color = "green" if pos['pnl'] >= 0 else "red"
            pos_table.add_row(
                pos['underlying'],
                f"${pos['strike']:.0f}",
                pos['expiration'],
                str(pos['quantity']),
                f"${pos['current_value']:,.0f}",
                f"[{pnl_color}]${pos['pnl']:,.0f}[/{pnl_color}]",
                str(pos['days_to_expiry'])
            )
        
        console.print(pos_table)


def display_options_analysis(symbol: str, current_price: float, candidates: list, otm_percentage: float):
    """Display options analysis results."""
    
    target_strike = current_price * (1 - otm_percentage)
    
    console.print(f"\n[bold]Target Strike Price:[/bold] ${target_strike:.2f} ({otm_percentage:.1%} OTM)")
    
    if not candidates:
        console.print("[red]No suitable options found[/red]")
        return
    
    # Options table
    options_table = Table(title=f"Tail Hedging Candidates for {symbol}")
    options_table.add_column("Strike", style="white")
    options_table.add_column("Expiration", style="white")
    options_table.add_column("DTE", style="yellow")
    options_table.add_column("Bid", style="green")
    options_table.add_column("Ask", style="red")
    options_table.add_column("Last", style="white")
    options_table.add_column("Volume", style="cyan")
    options_table.add_column("OI", style="cyan")
    
    for option in candidates[:10]:  # Show top 10
        dte = (option.expiration - date.today()).days
        options_table.add_row(
            f"${option.strike:.0f}",
            option.expiration.strftime('%Y-%m-%d'),
            str(dte),
            f"${option.bid:.2f}",
            f"${option.ask:.2f}",
            f"${option.last:.2f}",
            str(option.volume),
            str(option.open_interest)
        )
    
    console.print(options_table)


if __name__ == "__main__":
    cli()