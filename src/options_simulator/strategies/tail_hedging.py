"""Universa-style tail hedging strategy implementation."""

from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from ..models.options import OptionContract, BlackScholesCalculator, TailHedgingAnalyzer
from ..data.providers import MarketDataManager
from ..config import StrategyConfig, settings


@dataclass
class Position:
    """Represents an options position."""
    contract: OptionContract
    quantity: int
    entry_price: float
    entry_date: date
    current_value: float = 0.0
    pnl: float = 0.0
    
    def update_value(self, current_price: float):
        """Update current value and P&L."""
        self.current_value = current_price * self.quantity * 100  # Options are per 100 shares
        self.pnl = self.current_value - (self.entry_price * self.quantity * 100)


@dataclass
class Portfolio:
    """Portfolio containing stock positions and options hedges."""
    cash: float
    stock_value: float
    positions: List[Position] = field(default_factory=list)
    
    @property
    def total_value(self) -> float:
        """Calculate total portfolio value."""
        options_value = sum(pos.current_value for pos in self.positions)
        return self.cash + self.stock_value + options_value
    
    @property
    def options_allocation(self) -> float:
        """Calculate percentage allocated to options."""
        options_value = sum(pos.current_value for pos in self.positions)
        return options_value / self.total_value if self.total_value > 0 else 0.0


class TailHedgingStrategy:
    """Universa-style tail hedging strategy implementation."""
    
    def __init__(self, config: StrategyConfig, data_manager: MarketDataManager):
        self.config = config
        self.data_manager = data_manager
        self.calculator = BlackScholesCalculator()
        self.analyzer = TailHedgingAnalyzer()
        
        # Initialize portfolio
        self.portfolio = Portfolio(
            cash=config.portfolio_value * (1 - config.hedge_allocation),
            stock_value=config.portfolio_value * (1 - config.hedge_allocation)
        )
        
        # Track performance metrics
        self.performance_history = []
        self.trade_history = []
        
    def find_optimal_puts(
        self, symbol: str, current_price: float, target_dte: int = 45
    ) -> List[OptionContract]:
        """Find optimal put options for tail hedging."""
        
        # Get options chain
        contracts = self.data_manager.get_options_chain(symbol)
        
        # Filter for puts
        puts = [c for c in contracts if c.option_type == 'put']
        
        # Calculate target strike (OTM percentage)
        target_strike = current_price * (1 - self.config.otm_percentage)
        
        # Filter by expiration (target DTE +/- 15 days)
        target_date = date.today() + timedelta(days=target_dte)
        min_date = target_date - timedelta(days=15)
        max_date = target_date + timedelta(days=15)
        
        candidates = []
        for put in puts:
            # Check expiration range
            if not (min_date <= put.expiration <= max_date):
                continue
                
            # Check if sufficiently out-of-the-money
            if put.strike > target_strike * 1.1:  # Too close to money
                continue
                
            # Check liquidity (basic filter)
            if put.volume == 0 and put.open_interest < 100:
                continue
                
            # Must have reasonable bid
            if put.bid <= 0:
                continue
                
            candidates.append(put)
        
        # Sort by strike price (prefer closer to target) and volume
        candidates.sort(key=lambda x: (abs(x.strike - target_strike), -x.volume))
        
        return candidates[:5]  # Return top 5 candidates
    
    def calculate_position_size(
        self, option_price: float, available_capital: float
    ) -> int:
        """Calculate number of contracts to buy."""
        contract_cost = option_price * 100  # Options are per 100 shares
        transaction_cost = settings.transaction_cost_per_contract
        total_cost_per_contract = contract_cost + transaction_cost
        
        max_contracts = int(available_capital / total_cost_per_contract)
        return max(0, max_contracts)
    
    def execute_trade(
        self, contract: OptionContract, quantity: int, price: float
    ) -> Position:
        """Execute a trade and add position to portfolio."""
        
        total_cost = (price * quantity * 100) + (settings.transaction_cost_per_contract * quantity)
        
        if total_cost > self.portfolio.cash:
            raise ValueError(f"Insufficient cash for trade. Need ${total_cost}, have ${self.portfolio.cash}")
        
        # Create position
        position = Position(
            contract=contract,
            quantity=quantity,
            entry_price=price,
            entry_date=date.today()
        )
        
        # Update portfolio
        self.portfolio.cash -= total_cost
        self.portfolio.positions.append(position)
        
        # Record trade
        trade_record = {
            'date': date.today(),
            'action': 'BUY',
            'symbol': contract.symbol,
            'underlying': contract.underlying,
            'strike': contract.strike,
            'expiration': contract.expiration,
            'quantity': quantity,
            'price': price,
            'total_cost': total_cost
        }
        self.trade_history.append(trade_record)
        
        print(f"Executed: BUY {quantity} {contract.underlying} {contract.strike}P {contract.expiration} @ ${price:.2f}")
        
        return position
    
    def close_position(self, position: Position, current_price: float) -> float:
        """Close a position and realize P&L."""
        
        proceeds = (current_price * position.quantity * 100) - (settings.transaction_cost_per_contract * position.quantity)
        
        # Update portfolio
        self.portfolio.cash += proceeds
        self.portfolio.positions.remove(position)
        
        # Calculate realized P&L
        realized_pnl = proceeds - (position.entry_price * position.quantity * 100)
        
        # Record trade
        trade_record = {
            'date': date.today(),
            'action': 'SELL',
            'symbol': position.contract.symbol,
            'underlying': position.contract.underlying,
            'strike': position.contract.strike,
            'expiration': position.contract.expiration,
            'quantity': position.quantity,
            'price': current_price,
            'proceeds': proceeds,
            'realized_pnl': realized_pnl
        }
        self.trade_history.append(trade_record)
        
        print(f"Closed: SELL {position.quantity} {position.contract.underlying} {position.contract.strike}P @ ${current_price:.2f} (P&L: ${realized_pnl:.2f})")
        
        return realized_pnl
    
    def check_rolling_conditions(self, position: Position) -> bool:
        """Check if position should be rolled (closed and replaced)."""
        
        days_to_expiry = (position.contract.expiration - date.today()).days
        
        # Roll if approaching expiration
        if days_to_expiry <= self.config.rolling_days:
            return True
        
        # Roll if position has gained significantly (take profits on vol spike)
        if position.pnl > position.entry_price * position.quantity * 100 * 2:  # 200% gain
            return True
        
        return False
    
    def update_portfolio_values(self, market_data: Dict[str, float]):
        """Update portfolio values based on current market data."""
        
        # Update stock value (assuming portfolio moves with market)
        # This is simplified - in reality you'd track individual holdings
        total_portfolio_change = 0
        for symbol in self.config.underlying_symbols:
            if symbol in market_data:
                # Simplified: assume equal weight in underlying positions
                weight = 1.0 / len(self.config.underlying_symbols)
                total_portfolio_change += weight * (market_data[symbol] - market_data.get(f"{symbol}_previous", market_data[symbol]))
        
        # Update stock portion of portfolio
        stock_return = total_portfolio_change / sum(market_data[s] for s in self.config.underlying_symbols if s in market_data)
        self.portfolio.stock_value *= (1 + stock_return)
        
        # Update options positions
        for position in self.portfolio.positions:
            symbol = position.contract.underlying
            if symbol in market_data:
                current_price = market_data[symbol]
                
                # Calculate time to expiry
                tte = self.calculator.days_to_expiration(position.contract.expiration)
                
                # Estimate option price using Black-Scholes
                # Note: This uses estimated volatility - in practice you'd use market prices
                estimated_price = self.calculator.calculate_price(
                    underlying_price=current_price,
                    strike=position.contract.strike,
                    time_to_expiry=tte,
                    risk_free_rate=settings.risk_free_rate,
                    volatility=settings.default_volatility,
                    option_type=position.contract.option_type
                )
                
                position.update_value(estimated_price)
    
    def rebalance_portfolio(self):
        """Rebalance portfolio according to strategy rules."""
        
        available_hedge_capital = self.portfolio.total_value * self.config.hedge_allocation
        current_hedge_value = sum(pos.current_value for pos in self.portfolio.positions)
        
        # Check positions for rolling
        positions_to_roll = []
        for position in self.portfolio.positions:
            if self.check_rolling_conditions(position):
                positions_to_roll.append(position)
        
        # Close positions that need rolling
        for position in positions_to_roll:
            # Estimate current price for closing (simplified)
            current_price = max(position.entry_price * 0.1, position.contract.bid)  # Simplified
            self.close_position(position, current_price)
        
        # Calculate remaining capital for new positions
        remaining_capital = available_hedge_capital - sum(pos.current_value for pos in self.portfolio.positions)
        
        if remaining_capital > 1000:  # Minimum threshold for new positions
            self._establish_new_positions(remaining_capital)
    
    def _establish_new_positions(self, available_capital: float):
        """Establish new tail hedging positions."""
        
        capital_per_symbol = available_capital / len(self.config.underlying_symbols)
        
        for symbol in self.config.underlying_symbols:
            try:
                current_price = self.data_manager.get_stock_price(symbol)
                if current_price == 0:
                    continue
                
                # Find optimal puts
                candidates = self.find_optimal_puts(symbol, current_price, self.config.target_dte)
                
                if not candidates:
                    print(f"No suitable put options found for {symbol}")
                    continue
                
                # Select best candidate (first in sorted list)
                best_put = candidates[0]
                
                # Use mid price or last price
                option_price = best_put.last if best_put.last > 0 else (best_put.bid + best_put.ask) / 2
                if option_price <= 0:
                    continue
                
                # Calculate position size
                quantity = self.calculate_position_size(option_price, capital_per_symbol)
                
                if quantity > 0:
                    self.execute_trade(best_put, quantity, option_price)
                
            except Exception as e:
                print(f"Error establishing position for {symbol}: {e}")
    
    def run_strategy_step(self, market_data: Dict[str, float]):
        """Execute one step of the strategy."""
        
        # Update portfolio values
        self.update_portfolio_values(market_data)
        
        # Record performance
        performance_record = {
            'date': date.today(),
            'total_value': self.portfolio.total_value,
            'cash': self.portfolio.cash,
            'stock_value': self.portfolio.stock_value,
            'options_value': sum(pos.current_value for pos in self.portfolio.positions),
            'options_allocation': self.portfolio.options_allocation,
            'num_positions': len(self.portfolio.positions)
        }
        self.performance_history.append(performance_record)
        
        # Rebalance if needed
        self.rebalance_portfolio()
    
    def get_performance_summary(self) -> Dict:
        """Get strategy performance summary."""
        
        if not self.performance_history:
            return {}
        
        initial_value = self.config.portfolio_value
        current_value = self.portfolio.total_value
        
        # Calculate returns
        total_return = (current_value - initial_value) / initial_value
        
        # Calculate hedge costs
        total_premiums_paid = sum(
            trade['total_cost'] for trade in self.trade_history 
            if trade['action'] == 'BUY'
        )
        
        hedge_cost_pct = total_premiums_paid / initial_value
        
        # Get current positions summary
        current_positions = []
        for pos in self.portfolio.positions:
            current_positions.append({
                'underlying': pos.contract.underlying,
                'strike': pos.contract.strike,
                'expiration': pos.contract.expiration.strftime('%Y-%m-%d'),
                'quantity': pos.quantity,
                'current_value': pos.current_value,
                'pnl': pos.pnl,
                'days_to_expiry': (pos.contract.expiration - date.today()).days
            })
        
        return {
            'initial_value': initial_value,
            'current_value': current_value,
            'total_return': total_return,
            'total_premiums_paid': total_premiums_paid,
            'hedge_cost_percentage': hedge_cost_pct,
            'options_allocation': self.portfolio.options_allocation,
            'num_trades': len(self.trade_history),
            'current_positions': current_positions,
            'cash': self.portfolio.cash
        }