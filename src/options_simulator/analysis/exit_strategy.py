"""
Exit Strategy Management for Tail Hedging Positions.

This module manages profit-taking and exit strategies for tail hedging positions,
focusing on capturing gains during black swan events before expiration.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ExitTriggerType(Enum):
    """Types of exit triggers for tail hedging positions."""
    VIX_SPIKE = "vix_spike"              # Exit when VIX spikes above threshold
    PORTFOLIO_PROTECTION = "portfolio_protection"  # Exit when portfolio drawdown occurs
    PROFIT_TARGET = "profit_target"      # Exit when profit target is reached
    TIME_DECAY = "time_decay"           # Exit before excessive time decay
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # Exit when correlations spike
    LIQUIDITY_STRESS = "liquidity_stress"  # Exit when market liquidity deteriorates


@dataclass
class ExitTrigger:
    """Configuration for an exit trigger."""
    trigger_type: ExitTriggerType
    threshold: float
    partial_exit_percentage: float = 0.5  # Percentage of position to exit
    priority: int = 1  # Higher number = higher priority
    enabled: bool = True


@dataclass
class ExitOpportunity:
    """Represents a profit-taking opportunity."""
    timestamp: datetime
    trigger_type: ExitTriggerType
    market_conditions: Dict[str, float]
    position_pnl_multiplier: float  # e.g., 5.0 means 5x gain
    recommended_exit_percentage: float
    urgency_score: float  # 0-1, higher = more urgent
    rationale: str


@dataclass
class ExitExecution:
    """Record of an executed exit."""
    timestamp: datetime
    trigger_type: ExitTriggerType
    exit_percentage: float
    realized_pnl_multiplier: float
    market_conditions: Dict[str, float]
    transaction_cost: float


class ExitStrategyManager:
    """
    Manages exit strategies for tail hedging positions.
    
    Key Functionality:
    1. Define profit-taking triggers based on market conditions
    2. Monitor real-time market stress indicators
    3. Optimize partial liquidation timing
    4. Simulate historical exit opportunities
    5. Calculate impact of early exits on total strategy cost
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the exit strategy manager."""
        self.config = config or self._default_config()
        self.exit_history: List[ExitExecution] = []
        self.active_triggers: List[ExitTrigger] = self._initialize_triggers()
        
    def _default_config(self) -> Dict:
        """Default configuration for exit strategy management."""
        return {
            # VIX-based exit triggers
            "vix_spike_thresholds": {
                "moderate": 30,  # Take 25% of position
                "severe": 45,    # Take 50% of position  
                "extreme": 60    # Take 75% of position
            },
            
            # Profit-taking thresholds
            "profit_targets": [2.0, 5.0, 10.0, 20.0],  # 2x, 5x, 10x, 20x gains
            "profit_exit_percentages": [0.25, 0.40, 0.60, 0.80],
            
            # Portfolio protection triggers
            "portfolio_drawdown_thresholds": [0.05, 0.10, 0.15],  # 5%, 10%, 15% drawdowns
            "drawdown_exit_percentages": [0.30, 0.60, 0.90],
            
            # Time decay management
            "time_decay_threshold": 0.10,  # Exit if theta > 10% of position value per day
            "min_dte_for_exits": 7,  # Don't exit if less than 7 days to expiry
            
            # Market stress indicators
            "correlation_spike_threshold": 0.8,  # Exit if correlations > 80%
            "liquidity_stress_indicators": {
                "bid_ask_spread_multiplier": 3.0,  # Exit if spreads widen 3x
                "volume_drop_threshold": 0.5      # Exit if volume drops 50%
            },
            
            # Transaction costs
            "transaction_cost_bps": 5,  # 0.05% transaction cost
            "market_impact_threshold": 100000,  # $100k threshold for market impact
            
            # Risk management
            "max_single_exit": 0.75,  # Never exit more than 75% at once
            "min_position_remaining": 0.20,  # Always keep at least 20% position
            "cooling_off_period_hours": 6  # Wait 6 hours between major exits
        }
    
    def _initialize_triggers(self) -> List[ExitTrigger]:
        """Initialize default exit triggers."""
        triggers = []
        
        # VIX spike triggers
        vix_thresholds = self.config["vix_spike_thresholds"]
        triggers.extend([
            ExitTrigger(ExitTriggerType.VIX_SPIKE, vix_thresholds["moderate"], 0.25, priority=2),
            ExitTrigger(ExitTriggerType.VIX_SPIKE, vix_thresholds["severe"], 0.50, priority=3),
            ExitTrigger(ExitTriggerType.VIX_SPIKE, vix_thresholds["extreme"], 0.75, priority=4),
        ])
        
        # Profit target triggers  
        for i, (target, percentage) in enumerate(zip(
            self.config["profit_targets"], 
            self.config["profit_exit_percentages"]
        )):
            triggers.append(
                ExitTrigger(ExitTriggerType.PROFIT_TARGET, target, percentage, priority=i+1)
            )
            
        # Portfolio protection triggers
        for i, (drawdown, percentage) in enumerate(zip(
            self.config["portfolio_drawdown_thresholds"],
            self.config["drawdown_exit_percentages"] 
        )):
            triggers.append(
                ExitTrigger(ExitTriggerType.PORTFOLIO_PROTECTION, drawdown, percentage, priority=i+2)
            )
            
        return triggers
    
    def define_profit_taking_triggers(self, 
                                    custom_triggers: Optional[List[ExitTrigger]] = None) -> List[ExitTrigger]:
        """
        Define or update profit-taking triggers.
        
        Args:
            custom_triggers: Custom trigger configurations
            
        Returns:
            List of active exit triggers
        """
        if custom_triggers:
            self.active_triggers = custom_triggers
        
        # Sort by priority (higher priority first)
        self.active_triggers.sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Configured {len(self.active_triggers)} exit triggers")
        return self.active_triggers
    
    def monitor_market_stress_indicators(self, market_data: Dict[str, float]) -> Dict[str, float]:
        """
        Monitor real-time market stress indicators for exit opportunities.
        
        Args:
            market_data: Dictionary containing market data (VIX, correlations, volumes, etc.)
            
        Returns:
            Dict of stress indicator scores (0-1, higher = more stress)
        """
        stress_indicators = {}
        
        # VIX stress indicator
        vix_level = market_data.get("vix", 15)
        if vix_level < 15:
            stress_indicators["vix_stress"] = 0.0
        elif vix_level < 25:
            stress_indicators["vix_stress"] = (vix_level - 15) / 10
        elif vix_level < 40:
            stress_indicators["vix_stress"] = 0.5 + (vix_level - 25) / 30
        else:
            stress_indicators["vix_stress"] = min(1.0, 0.8 + (vix_level - 40) / 40)
            
        # Correlation stress (higher correlations = more stress)
        correlation = market_data.get("average_correlation", 0.5)
        stress_indicators["correlation_stress"] = max(0, (correlation - 0.5) / 0.4)
        
        # Liquidity stress (wider spreads, lower volume = more stress)
        bid_ask_spread = market_data.get("bid_ask_spread_ratio", 1.0)
        volume_ratio = market_data.get("volume_ratio", 1.0)  # current/average
        
        spread_stress = min(1.0, max(0, (bid_ask_spread - 1.0) / 2.0))
        volume_stress = max(0, (1.0 - volume_ratio) / 0.5)
        stress_indicators["liquidity_stress"] = (spread_stress + volume_stress) / 2
        
        # Portfolio drawdown stress
        portfolio_drawdown = abs(market_data.get("portfolio_return", 0))
        stress_indicators["drawdown_stress"] = min(1.0, portfolio_drawdown / 0.20)  # 20% max
        
        # Calculate overall stress score
        weights = {"vix_stress": 0.4, "correlation_stress": 0.2, 
                  "liquidity_stress": 0.2, "drawdown_stress": 0.2}
        overall_stress = sum(stress_indicators[k] * weights[k] for k in weights)
        stress_indicators["overall_stress"] = overall_stress
        
        return stress_indicators
    
    def optimize_partial_liquidation_timing(self, 
                                          current_position_value: float,
                                          market_conditions: Dict[str, float],
                                          position_pnl_multiplier: float) -> ExitOpportunity:
        """
        Optimize timing for partial position liquidation.
        
        Args:
            current_position_value: Current value of the position
            market_conditions: Current market conditions
            position_pnl_multiplier: Current P&L multiplier (e.g., 3.0 = 3x gain)
            
        Returns:
            Optimal exit opportunity recommendation
        """
        stress_indicators = self.monitor_market_stress_indicators(market_conditions)
        
        # Check active triggers
        triggered_exits = []
        for trigger in self.active_triggers:
            if not trigger.enabled:
                continue
                
            triggered = False
            if trigger.trigger_type == ExitTriggerType.VIX_SPIKE:
                triggered = market_conditions.get("vix", 15) >= trigger.threshold
            elif trigger.trigger_type == ExitTriggerType.PROFIT_TARGET:
                triggered = position_pnl_multiplier >= trigger.threshold
            elif trigger.trigger_type == ExitTriggerType.PORTFOLIO_PROTECTION:
                drawdown = abs(market_conditions.get("portfolio_return", 0))
                triggered = drawdown >= trigger.threshold
            elif trigger.trigger_type == ExitTriggerType.CORRELATION_BREAKDOWN:
                correlation = market_conditions.get("average_correlation", 0.5)
                triggered = correlation >= trigger.threshold
                
            if triggered:
                triggered_exits.append(trigger)
                
        if not triggered_exits:
            # No triggers activated
            return ExitOpportunity(
                timestamp=datetime.now(),
                trigger_type=ExitTriggerType.TIME_DECAY,
                market_conditions=market_conditions,
                position_pnl_multiplier=position_pnl_multiplier,
                recommended_exit_percentage=0.0,
                urgency_score=0.0,
                rationale="No exit triggers activated"
            )
        
        # Select highest priority trigger
        primary_trigger = max(triggered_exits, key=lambda x: x.priority)
        
        # Calculate urgency score based on multiple factors
        urgency_factors = {
            "stress_level": stress_indicators["overall_stress"],
            "profit_magnitude": min(1.0, position_pnl_multiplier / 10.0),
            "trigger_priority": primary_trigger.priority / 5.0,
            "market_momentum": self._assess_market_momentum(market_conditions)
        }
        
        urgency_score = np.mean(list(urgency_factors.values()))
        
        # Adjust exit percentage based on urgency and multiple trigger activation
        base_exit_percentage = primary_trigger.partial_exit_percentage
        
        # Increase exit percentage if multiple triggers are active
        if len(triggered_exits) > 1:
            base_exit_percentage *= 1.2
            
        # Adjust based on urgency
        urgency_multiplier = 1.0 + (urgency_score * 0.5)
        recommended_exit_percentage = min(
            self.config["max_single_exit"],
            base_exit_percentage * urgency_multiplier
        )
        
        # Generate rationale
        rationale_parts = [f"{primary_trigger.trigger_type.value} triggered"]
        if len(triggered_exits) > 1:
            rationale_parts.append(f"+ {len(triggered_exits)-1} other triggers")
        rationale_parts.append(f"Urgency: {urgency_score:.2f}")
        rationale = ", ".join(rationale_parts)
        
        return ExitOpportunity(
            timestamp=datetime.now(),
            trigger_type=primary_trigger.trigger_type,
            market_conditions=market_conditions,
            position_pnl_multiplier=position_pnl_multiplier,
            recommended_exit_percentage=recommended_exit_percentage,
            urgency_score=urgency_score,
            rationale=rationale
        )
    
    def _assess_market_momentum(self, market_conditions: Dict[str, float]) -> float:
        """Assess market momentum for exit timing (0-1 scale)."""
        # Simple momentum assessment based on VIX change
        vix_change = market_conditions.get("vix_daily_change", 0)
        momentum = min(1.0, max(0.0, vix_change / 20.0))  # Normalize to 0-1
        return momentum
    
    def simulate_early_exit_scenarios(self, 
                                    historical_data: pd.DataFrame,
                                    position_parameters: Dict) -> List[Dict]:
        """
        Simulate historical early exit scenarios to understand profit potential.
        
        Args:
            historical_data: Historical market data with VIX, returns, etc.
            position_parameters: Position setup parameters
            
        Returns:
            List of simulated exit scenarios with outcomes
        """
        scenarios = []
        
        # Key historical stress events for simulation
        stress_events = [
            {"name": "COVID-19 Crash", "start": "2020-02-20", "end": "2020-03-23"},
            {"name": "August 2015 Flash", "start": "2015-08-20", "end": "2015-08-25"},
            {"name": "February 2018 VIX Spike", "start": "2018-02-05", "end": "2018-02-09"},
            {"name": "October 2018 Selloff", "start": "2018-10-01", "end": "2018-10-30"},
        ]
        
        for event in stress_events:
            try:
                # Filter data for event period
                event_data = historical_data.loc[event["start"]:event["end"]]
                if event_data.empty:
                    continue
                    
                # Simulate position performance during event
                scenario = self._simulate_single_event_exits(
                    event_data, 
                    event["name"], 
                    position_parameters
                )
                scenarios.append(scenario)
                
            except Exception as e:
                logger.warning(f"Failed to simulate {event['name']}: {e}")
                continue
                
        return scenarios
    
    def _simulate_single_event_exits(self, 
                                   event_data: pd.DataFrame,
                                   event_name: str,
                                   position_params: Dict) -> Dict:
        """Simulate exits for a single historical event."""
        # Simplified simulation - in practice would use actual option pricing
        max_vix = event_data.get("vix", pd.Series([15])).max()
        max_drawdown = abs(event_data.get("spy_return", pd.Series([0])).min())
        
        # Estimate option appreciation based on VIX spike and market drawdown
        # This is a rough approximation - real implementation would use option pricing models
        vix_multiplier = 1 + (max_vix - 15) / 10  # Rough VIX impact
        drawdown_multiplier = 1 + max_drawdown * 20  # Rough drawdown impact
        
        estimated_peak_pnl = vix_multiplier * drawdown_multiplier
        
        # Determine optimal exit points
        exit_opportunities = []
        for i, (date, row) in enumerate(event_data.iterrows()):
            market_conditions = {
                "vix": row.get("vix", 20),
                "portfolio_return": row.get("spy_return", 0),
                "average_correlation": 0.7 + (row.get("vix", 20) - 20) * 0.01
            }
            
            current_pnl = min(estimated_peak_pnl, 1 + (row.get("vix", 20) - 15) / 5)
            
            exit_opp = self.optimize_partial_liquidation_timing(
                current_position_value=10000,  # Example position size
                market_conditions=market_conditions,
                position_pnl_multiplier=current_pnl
            )
            
            if exit_opp.recommended_exit_percentage > 0:
                exit_opportunities.append({
                    "date": date,
                    "pnl_multiplier": current_pnl,
                    "exit_percentage": exit_opp.recommended_exit_percentage,
                    "trigger": exit_opp.trigger_type.value
                })
        
        return {
            "event_name": event_name,
            "peak_pnl_multiplier": estimated_peak_pnl,
            "total_exit_opportunities": len(exit_opportunities),
            "best_exit_pnl": max([opp["pnl_multiplier"] for opp in exit_opportunities], default=1.0),
            "exit_timeline": exit_opportunities
        }
    
    def calculate_profit_realization_impact(self, 
                                          exit_scenarios: List[Dict],
                                          base_strategy_cost: float) -> Dict[str, float]:
        """
        Calculate how early exits impact total strategy cost through profit realization.
        
        Args:
            exit_scenarios: List of simulated exit scenarios
            base_strategy_cost: Base annual cost of strategy without exits
            
        Returns:
            Dict with cost impact analysis
        """
        if not exit_scenarios:
            return {"net_cost_reduction": 0.0, "break_even_probability": 0.0}
        
        # Calculate average profit realization across scenarios
        total_realized_profits = 0
        profitable_scenarios = 0
        
        for scenario in exit_scenarios:
            best_exit = scenario.get("best_exit_pnl", 1.0)
            if best_exit > 1.5:  # At least 50% profit required to be meaningful
                # Assume we exit 50% of position at best opportunity
                realized_profit = (best_exit - 1.0) * 0.5
                total_realized_profits += realized_profit
                profitable_scenarios += 1
        
        avg_annual_profit_realization = total_realized_profits / len(exit_scenarios)
        
        # Convert to cost impact (profits reduce net strategy cost)
        annual_cost_reduction = avg_annual_profit_realization * base_strategy_cost
        net_strategy_cost = base_strategy_cost - annual_cost_reduction
        
        cost_reduction_percentage = (annual_cost_reduction / base_strategy_cost) * 100
        break_even_probability = profitable_scenarios / len(exit_scenarios)
        
        return {
            "base_annual_cost": base_strategy_cost,
            "average_annual_profit_realization": avg_annual_profit_realization,
            "annual_cost_reduction": annual_cost_reduction,
            "net_annual_cost": net_strategy_cost,
            "cost_reduction_percentage": cost_reduction_percentage,
            "break_even_probability": break_even_probability,
            "profitable_scenario_count": profitable_scenarios,
            "total_scenarios_analyzed": len(exit_scenarios)
        }
    
    def assess_exit_vs_hold_tradeoffs(self, 
                                    current_conditions: Dict[str, float],
                                    position_details: Dict) -> Dict[str, any]:
        """
        Assess the tradeoffs between exiting now vs holding to expiration.
        
        Args:
            current_conditions: Current market conditions
            position_details: Details about the current position
            
        Returns:
            Analysis of exit vs hold tradeoffs
        """
        current_pnl = position_details.get("current_pnl_multiplier", 1.0)
        days_to_expiry = position_details.get("days_to_expiry", 45)
        
        # Exit scenario analysis
        exit_opp = self.optimize_partial_liquidation_timing(
            current_position_value=position_details.get("position_value", 10000),
            market_conditions=current_conditions,
            position_pnl_multiplier=current_pnl
        )
        
        # Hold scenario analysis
        hold_scenarios = self._analyze_hold_scenarios(current_conditions, days_to_expiry)
        
        # Transaction cost impact
        transaction_cost = (position_details.get("position_value", 10000) * 
                          self.config["transaction_cost_bps"] / 10000)
        
        tradeoff_analysis = {
            "current_position": {
                "pnl_multiplier": current_pnl,
                "days_to_expiry": days_to_expiry,
                "position_value": position_details.get("position_value", 10000)
            },
            "exit_scenario": {
                "recommended_exit_percentage": exit_opp.recommended_exit_percentage,
                "immediate_realized_pnl": (current_pnl - 1.0) * exit_opp.recommended_exit_percentage,
                "transaction_cost": transaction_cost * exit_opp.recommended_exit_percentage,
                "urgency_score": exit_opp.urgency_score,
                "trigger": exit_opp.trigger_type.value
            },
            "hold_scenario": hold_scenarios,
            "recommendation": {
                "action": "exit" if exit_opp.urgency_score > 0.6 else "hold",
                "confidence": exit_opp.urgency_score,
                "rationale": exit_opp.rationale
            }
        }
        
        return tradeoff_analysis
    
    def _analyze_hold_scenarios(self, current_conditions: Dict, days_to_expiry: int) -> Dict:
        """Analyze potential outcomes of holding position to expiration."""
        vix_level = current_conditions.get("vix", 20)
        
        # Estimate probabilities of different outcomes
        if days_to_expiry > 30:
            # More time = higher chance of volatility mean reversion
            prob_further_stress = 0.3 if vix_level > 30 else 0.1
            prob_mean_reversion = 0.6 if vix_level > 30 else 0.3
            prob_unchanged = 1.0 - prob_further_stress - prob_mean_reversion
        else:
            # Less time = more likely to expire as-is
            prob_further_stress = 0.2 if vix_level > 30 else 0.05
            prob_mean_reversion = 0.8 if vix_level > 30 else 0.2
            prob_unchanged = 1.0 - prob_further_stress - prob_mean_reversion
        
        return {
            "days_remaining": days_to_expiry,
            "scenario_probabilities": {
                "further_stress": prob_further_stress,
                "mean_reversion": prob_mean_reversion,
                "unchanged": prob_unchanged
            },
            "expected_outcomes": {
                "further_stress_pnl": 3.0,  # Could triple if more stress
                "mean_reversion_pnl": 0.5,  # Lose half if volatility drops
                "unchanged_pnl": 1.0       # Break even if unchanged
            },
            "time_decay_risk": min(0.5, days_to_expiry / 60),  # Higher risk closer to expiry
            "expected_hold_pnl": (prob_further_stress * 3.0 + 
                                prob_mean_reversion * 0.5 + 
                                prob_unchanged * 1.0)
        }
    
    def model_black_swan_appreciation_patterns(self, 
                                             historical_events: Optional[List[Dict]] = None) -> Dict[str, any]:
        """
        Model how put options typically appreciate during black swan events.
        
        This provides insights into optimal profit-taking timing during crisis events.
        """
        # Default black swan events with typical option appreciation patterns
        default_events = [
            {
                "name": "COVID-19 Crash",
                "duration_days": 23,
                "max_market_decline": -0.34,
                "vix_peak": 82,
                "typical_put_appreciation": {
                    "day_1": 2.0,   # 2x on first day
                    "day_5": 8.0,   # 8x after 5 days
                    "day_10": 15.0, # 15x at peak
                    "day_15": 12.0, # Some decline from peak
                    "day_23": 8.0   # Still elevated at end
                }
            },
            {
                "name": "2008 Financial Crisis",
                "duration_days": 180,
                "max_market_decline": -0.57,
                "vix_peak": 80,
                "typical_put_appreciation": {
                    "day_1": 1.5,
                    "day_30": 3.0,
                    "day_60": 8.0,
                    "day_120": 12.0,
                    "day_180": 5.0
                }
            }
        ]
        
        events_to_analyze = historical_events or default_events
        
        # Analyze appreciation patterns
        appreciation_analysis = {
            "typical_patterns": {},
            "optimal_exit_windows": {},
            "risk_factors": {}
        }
        
        for event in events_to_analyze:
            event_name = event["name"]
            appreciation_curve = event["typical_put_appreciation"]
            
            # Find optimal exit points
            max_appreciation_day = max(appreciation_curve.keys(), 
                                     key=lambda k: appreciation_curve[k])
            max_appreciation = appreciation_curve[max_appreciation_day]
            
            # Identify good exit windows (appreciation > 5x and still growing or stable)
            good_exit_days = []
            for day, mult in appreciation_curve.items():
                if mult >= 5.0:
                    good_exit_days.append((day, mult))
            
            appreciation_analysis["typical_patterns"][event_name] = {
                "peak_appreciation": max_appreciation,
                "peak_day": max_appreciation_day,
                "appreciation_curve": appreciation_curve
            }
            
            appreciation_analysis["optimal_exit_windows"][event_name] = {
                "good_exit_opportunities": good_exit_days,
                "recommended_strategy": "Partial exits at 5x, 10x, and 15x levels"
            }
            
            # Risk factors for each event type
            appreciation_analysis["risk_factors"][event_name] = {
                "volatility_mean_reversion_risk": "High" if event["duration_days"] < 30 else "Medium",
                "liquidity_risk": "High" if max_appreciation > 10 else "Medium",
                "timing_sensitivity": "High" if max_appreciation > 15 else "Medium"
            }
        
        # General insights
        appreciation_analysis["general_insights"] = {
            "median_peak_appreciation": np.median([
                analysis["peak_appreciation"] 
                for analysis in appreciation_analysis["typical_patterns"].values()
            ]),
            "typical_peak_timing": "Days 5-15 for short-term events, Days 60-120 for extended events",
            "key_profit_taking_levels": [5.0, 10.0, 15.0],
            "recommended_exit_strategy": "Staged exits: 25% at 5x, 35% at 10x, 40% at 15x"
        }
        
        return appreciation_analysis
    
    def generate_exit_strategy_report(self, 
                                    current_positions: List[Dict],
                                    market_conditions: Dict[str, float]) -> Dict[str, any]:
        """
        Generate comprehensive exit strategy report for current positions.
        
        Args:
            current_positions: List of current position details
            market_conditions: Current market conditions
            
        Returns:
            Comprehensive exit strategy report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "market_conditions": market_conditions,
            "position_analysis": [],
            "overall_recommendations": {},
            "risk_assessment": {}
        }
        
        total_position_value = 0
        total_unrealized_pnl = 0
        exit_recommendations = []
        
        for position in current_positions:
            position_value = position.get("value", 0)
            pnl_multiplier = position.get("pnl_multiplier", 1.0)
            
            total_position_value += position_value
            total_unrealized_pnl += position_value * (pnl_multiplier - 1.0)
            
            # Analyze each position
            exit_opp = self.optimize_partial_liquidation_timing(
                current_position_value=position_value,
                market_conditions=market_conditions,
                position_pnl_multiplier=pnl_multiplier
            )
            
            tradeoff_analysis = self.assess_exit_vs_hold_tradeoffs(
                current_conditions=market_conditions,
                position_details=position
            )
            
            position_analysis = {
                "position_id": position.get("id", "unknown"),
                "current_value": position_value,
                "pnl_multiplier": pnl_multiplier,
                "days_to_expiry": position.get("days_to_expiry", 45),
                "exit_opportunity": {
                    "recommended_exit_percentage": exit_opp.recommended_exit_percentage,
                    "urgency_score": exit_opp.urgency_score,
                    "trigger_type": exit_opp.trigger_type.value,
                    "rationale": exit_opp.rationale
                },
                "tradeoff_analysis": tradeoff_analysis
            }
            
            report["position_analysis"].append(position_analysis)
            
            if exit_opp.recommended_exit_percentage > 0:
                exit_recommendations.append({
                    "position_id": position.get("id"),
                    "exit_percentage": exit_opp.recommended_exit_percentage,
                    "urgency": exit_opp.urgency_score
                })
        
        # Overall recommendations
        stress_indicators = self.monitor_market_stress_indicators(market_conditions)
        
        report["overall_recommendations"] = {
            "immediate_action_required": any(rec["urgency"] > 0.7 for rec in exit_recommendations),
            "total_positions_with_exit_signals": len(exit_recommendations),
            "aggregate_stress_score": stress_indicators["overall_stress"],
            "recommended_actions": self._generate_action_recommendations(
                exit_recommendations, stress_indicators
            )
        }
        
        # Risk assessment
        report["risk_assessment"] = {
            "total_position_value": total_position_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "portfolio_risk_score": self._assess_portfolio_risk(
                current_positions, market_conditions
            ),
            "key_risks": self._identify_key_risks(current_positions, market_conditions)
        }
        
        return report
    
    def _generate_action_recommendations(self, 
                                       exit_recommendations: List[Dict],
                                       stress_indicators: Dict[str, float]) -> List[str]:
        """Generate specific action recommendations."""
        actions = []
        
        high_urgency_exits = [rec for rec in exit_recommendations if rec["urgency"] > 0.7]
        medium_urgency_exits = [rec for rec in exit_recommendations if 0.4 <= rec["urgency"] <= 0.7]
        
        if high_urgency_exits:
            actions.append(f"IMMEDIATE: Execute {len(high_urgency_exits)} high-urgency exits")
        
        if medium_urgency_exits:
            actions.append(f"Within 4 hours: Consider {len(medium_urgency_exits)} medium-urgency exits")
        
        if stress_indicators["overall_stress"] > 0.6:
            actions.append("Monitor market conditions closely - elevated stress detected")
        
        if stress_indicators.get("vix_stress", 0) > 0.8:
            actions.append("Consider scaling up exit percentages due to extreme VIX levels")
        
        return actions
    
    def _assess_portfolio_risk(self, positions: List[Dict], market_conditions: Dict) -> float:
        """Assess overall portfolio risk score (0-1)."""
        # Simplified risk assessment
        avg_pnl = np.mean([pos.get("pnl_multiplier", 1.0) for pos in positions])
        avg_dte = np.mean([pos.get("days_to_expiry", 45) for pos in positions])
        
        # Higher gains = higher risk of giving back profits
        pnl_risk = min(1.0, (avg_pnl - 1.0) / 10.0)
        
        # Shorter time to expiry = higher time decay risk  
        time_risk = max(0.0, 1.0 - avg_dte / 60.0)
        
        # Market volatility risk
        vol_risk = min(1.0, market_conditions.get("vix", 20) / 50.0)
        
        return (pnl_risk + time_risk + vol_risk) / 3.0
    
    def _identify_key_risks(self, positions: List[Dict], market_conditions: Dict) -> List[str]:
        """Identify key risks for the current portfolio."""
        risks = []
        
        avg_pnl = np.mean([pos.get("pnl_multiplier", 1.0) for pos in positions])
        min_dte = min([pos.get("days_to_expiry", 45) for pos in positions], default=45)
        vix_level = market_conditions.get("vix", 20)
        
        if avg_pnl > 5.0:
            risks.append("Profit-taking risk: Large unrealized gains vulnerable to reversal")
        
        if min_dte < 21:
            risks.append("Time decay risk: Positions approaching expiration")
        
        if vix_level > 40:
            risks.append("Volatility mean reversion risk: Extreme VIX levels may normalize")
        
        if market_conditions.get("average_correlation", 0.5) > 0.8:
            risks.append("Correlation risk: High correlations may indicate systemic stress")
        
        return risks