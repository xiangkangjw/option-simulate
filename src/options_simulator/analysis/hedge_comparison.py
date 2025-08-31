"""
Hedge Comparison Engine for SPX Tail Hedging Strategies.

This module provides comprehensive comparison capabilities between different
expiration strategies for tail hedging, incorporating volatility regime analysis
and dynamic exit strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

from ..models.jump_diffusion import JumpDiffusionPricer, JumpDiffusionParameters
from .volatility_regime import VolatilityRegimeAnalyzer, VolatilityRegime, RegimeAnalysis
from .exit_strategy import ExitStrategyManager, ExitOpportunity, ExitTrigger, ExitTriggerType
from ..config import EnhancedHedgingConfig

logger = logging.getLogger(__name__)


@dataclass
class HedgingStrategy:
    """Enhanced hedging strategy with regime awareness and exit management."""
    expiration_months: int
    otm_percentage: float
    rolling_threshold_days: int
    volatility_regime_adjustments: Dict[str, float]
    exit_triggers: List[ExitTrigger]
    
    # Strategy identification
    strategy_id: str = ""
    name: str = ""
    
    # Performance metrics (populated by analysis)
    annual_cost: Optional[float] = None
    protection_ratio: Optional[float] = None
    expected_returns_multiplier: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    def __post_init__(self):
        if not self.strategy_id:
            self.strategy_id = f"{self.expiration_months}M_{self.otm_percentage:.0%}_OTM"
        if not self.name:
            self.name = f"{self.expiration_months}-Month {self.otm_percentage:.0%} OTM Puts"
    
    def calculate_premium_cost(self, 
                             spot_price: float,
                             strike_price: float,
                             time_to_expiry: float,
                             risk_free_rate: float,
                             volatility: float,
                             pricer: JumpDiffusionPricer) -> float:
        """Calculate premium cost using jump-diffusion pricing."""
        return pricer.merton_jump_diffusion_price(
            S=spot_price,
            K=strike_price,
            T=time_to_expiry,
            r=risk_free_rate,
            option_type="put"
        )
    
    def calculate_regime_adjusted_greeks(self,
                                       spot_price: float,
                                       strike_price: float, 
                                       time_to_expiry: float,
                                       risk_free_rate: float,
                                       current_regime: VolatilityRegime,
                                       pricer: JumpDiffusionPricer) -> Dict[str, float]:
        """Calculate Greeks with volatility regime adjustments."""
        greeks = pricer.calculate_jump_adjusted_greeks(
            S=spot_price,
            K=strike_price,
            T=time_to_expiry,
            r=risk_free_rate,
            option_type="put"
        )
        
        # Apply regime adjustments
        regime_multiplier = self.volatility_regime_adjustments.get(current_regime.value, 1.0)
        
        adjusted_greeks = {
            "delta": greeks.delta * regime_multiplier,
            "gamma": greeks.gamma * regime_multiplier,
            "theta": greeks.theta * regime_multiplier,
            "vega": greeks.vega * regime_multiplier,
            "rho": greeks.rho,
            "jump_delta": greeks.jump_delta,
            "jump_gamma": greeks.jump_gamma
        }
        
        return adjusted_greeks
    
    def simulate_performance(self,
                           historical_data: pd.DataFrame,
                           portfolio_value: float,
                           exit_manager: ExitStrategyManager) -> Dict[str, float]:
        """Simulate historical performance with exit strategies."""
        # Simplified simulation - in practice would use detailed option pricing
        total_cost = 0
        total_profit = 0
        protection_events = 0
        
        # Estimate annual cost based on rolling frequency
        rolls_per_year = 12 / self.expiration_months
        estimated_annual_cost = portfolio_value * 0.02 * rolls_per_year  # 2% per roll estimate
        
        # Simulate major protection events
        stress_events = historical_data[historical_data.get('vix', pd.Series([15])) > 30]
        
        for _, event in stress_events.iterrows():
            # Estimate protection value during stress
            vix_level = event.get('vix', 30)
            market_return = event.get('spy_return', 0)
            
            if market_return < -0.05:  # 5%+ drawdown
                protection_events += 1
                
                # Estimate option appreciation
                stress_multiplier = min(20, vix_level / 5)  # Cap at 20x
                protection_value = estimated_annual_cost * stress_multiplier
                
                # Apply exit strategy
                market_conditions = {
                    'vix': vix_level,
                    'portfolio_return': market_return,
                    'average_correlation': 0.8
                }
                
                exit_opp = exit_manager.optimize_partial_liquidation_timing(
                    current_position_value=protection_value,
                    market_conditions=market_conditions,
                    position_pnl_multiplier=stress_multiplier
                )
                
                realized_profit = protection_value * exit_opp.recommended_exit_percentage
                total_profit += realized_profit
        
        return {
            "annual_cost": estimated_annual_cost,
            "total_protection_events": protection_events,
            "total_realized_profit": total_profit,
            "protection_ratio": total_profit / estimated_annual_cost if estimated_annual_cost > 0 else 0,
            "net_annual_cost": estimated_annual_cost - (total_profit / len(historical_data.index) * 252)
        }
    
    def evaluate_early_exit_opportunities(self,
                                        current_conditions: Dict[str, float],
                                        position_details: Dict,
                                        exit_manager: ExitStrategyManager) -> ExitOpportunity:
        """Evaluate current early exit opportunities."""
        return exit_manager.optimize_partial_liquidation_timing(
            current_position_value=position_details.get("position_value", 0),
            market_conditions=current_conditions,
            position_pnl_multiplier=position_details.get("pnl_multiplier", 1.0)
        )
    
    def model_volatility_term_structure_impact(self,
                                             current_vix: float,
                                             vol_analyzer: VolatilityRegimeAnalyzer) -> Dict[str, float]:
        """Model impact of volatility term structure on strategy cost."""
        term_structure = vol_analyzer.model_term_structure_dynamics(current_vix)
        
        # Get adjustment for this strategy's expiration
        expiry_days = self.expiration_months * 30
        
        # Find closest term structure point or interpolate
        if expiry_days in term_structure:
            vol_adjustment = term_structure[expiry_days]
        else:
            # Simple linear interpolation
            sorted_expirations = sorted(term_structure.keys())
            if expiry_days < min(sorted_expirations):
                vol_adjustment = term_structure[min(sorted_expirations)]
            elif expiry_days > max(sorted_expirations):
                vol_adjustment = term_structure[max(sorted_expirations)]
            else:
                # Find surrounding points and interpolate
                lower = max(exp for exp in sorted_expirations if exp <= expiry_days)
                upper = min(exp for exp in sorted_expirations if exp >= expiry_days)
                
                if lower == upper:
                    vol_adjustment = term_structure[lower]
                else:
                    weight = (expiry_days - lower) / (upper - lower)
                    vol_adjustment = (term_structure[lower] * (1 - weight) + 
                                    term_structure[upper] * weight)
        
        # Convert volatility adjustment to cost impact
        cost_impact_multiplier = 1.0 + vol_adjustment
        
        return {
            "volatility_adjustment": vol_adjustment,
            "cost_impact_multiplier": cost_impact_multiplier,
            "relative_efficiency": 1.0 / cost_impact_multiplier,
            "term_structure_penalty": max(0, vol_adjustment)
        }


class HedgeComparisonEngine:
    """
    Enhanced hedge comparison engine with regime-aware analysis.
    
    Provides comprehensive comparison between different SPX hedging strategies,
    incorporating volatility regime dynamics, exit strategy optimization,
    and jump-diffusion pricing for accurate tail risk assessment.
    """
    
    def __init__(self, config: Optional[EnhancedHedgingConfig] = None):
        """Initialize the hedge comparison engine."""
        self.config = config or EnhancedHedgingConfig()
        
        # Initialize core components
        self.volatility_regime_analyzer = VolatilityRegimeAnalyzer()
        self.exit_strategy_manager = ExitStrategyManager()
        self.jump_diffusion_pricer = JumpDiffusionPricer()
        
        # Analysis cache
        self._analysis_cache = {}
        
    def compare_strategies(self,
                         strategies: List[HedgingStrategy],
                         portfolio_value: float,
                         current_market_conditions: Dict[str, float],
                         historical_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Compare multiple hedging strategies across different dimensions.
        
        Args:
            strategies: List of hedging strategies to compare
            portfolio_value: Total portfolio value to hedge
            current_market_conditions: Current market data (VIX, prices, etc.)
            historical_data: Historical market data for backtesting
            
        Returns:
            Comprehensive comparison results
        """
        logger.info(f"Comparing {len(strategies)} hedging strategies")
        
        # Analyze current volatility regime
        current_vix = current_market_conditions.get("vix", 20)
        current_regime = self.volatility_regime_analyzer.classify_current_regime(current_vix)
        
        comparison_results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "portfolio_value": portfolio_value,
            "current_market_conditions": current_market_conditions,
            "current_volatility_regime": current_regime.value,
            "strategy_analysis": {},
            "relative_comparisons": {},
            "recommendations": {}
        }
        
        # Analyze each strategy
        strategy_results = []
        for strategy in strategies:
            logger.info(f"Analyzing strategy: {strategy.name}")
            
            strategy_analysis = self._analyze_single_strategy(
                strategy=strategy,
                portfolio_value=portfolio_value,
                current_regime=current_regime,
                current_conditions=current_market_conditions,
                historical_data=historical_data
            )
            
            comparison_results["strategy_analysis"][strategy.strategy_id] = strategy_analysis
            strategy_results.append((strategy, strategy_analysis))
        
        # Generate relative comparisons
        comparison_results["relative_comparisons"] = self._generate_relative_comparisons(strategy_results)
        
        # Generate recommendations
        comparison_results["recommendations"] = self._generate_intelligent_recommendations(
            strategy_results, current_regime, current_market_conditions
        )
        
        return comparison_results
    
    def _analyze_single_strategy(self,
                               strategy: HedgingStrategy,
                               portfolio_value: float,
                               current_regime: VolatilityRegime,
                               current_conditions: Dict[str, float],
                               historical_data: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Analyze a single hedging strategy comprehensively."""
        
        # Basic strategy parameters
        hedge_allocation = portfolio_value * 0.05  # 5% default allocation
        current_spot = current_conditions.get("spy_price", 400)  # Default SPY price
        strike_price = current_spot * (1 - strategy.otm_percentage)
        time_to_expiry = strategy.expiration_months / 12.0
        risk_free_rate = current_conditions.get("risk_free_rate", 0.05)
        
        analysis = {
            "strategy_details": asdict(strategy),
            "pricing_analysis": {},
            "greeks_analysis": {},
            "regime_impact_analysis": {},
            "exit_strategy_analysis": {},
            "performance_metrics": {},
            "risk_assessment": {}
        }
        
        # Pricing analysis with jump-diffusion
        jd_price = strategy.calculate_premium_cost(
            spot_price=current_spot,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            volatility=0.20,  # Base volatility
            pricer=self.jump_diffusion_pricer
        )
        
        # Black-Scholes comparison
        bs_price = self.jump_diffusion_pricer._black_scholes_price(
            S=current_spot,
            K=strike_price,
            T=time_to_expiry,
            r=risk_free_rate,
            sigma=0.20,
            option_type="put"
        )
        
        contracts_needed = hedge_allocation / (jd_price * 100)  # 100 shares per contract
        annual_cost = jd_price * contracts_needed * 100 * (12 / strategy.expiration_months)
        
        analysis["pricing_analysis"] = {
            "jump_diffusion_price": jd_price,
            "black_scholes_price": bs_price,
            "jump_risk_premium": (jd_price - bs_price) / bs_price if bs_price > 0 else 0,
            "contracts_needed": contracts_needed,
            "annual_cost": annual_cost,
            "cost_as_percentage": annual_cost / portfolio_value
        }
        
        # Greeks analysis
        greeks = strategy.calculate_regime_adjusted_greeks(
            spot_price=current_spot,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            risk_free_rate=risk_free_rate,
            current_regime=current_regime,
            pricer=self.jump_diffusion_pricer
        )
        
        analysis["greeks_analysis"] = greeks
        
        # Volatility regime impact analysis
        vol_impact = strategy.model_volatility_term_structure_impact(
            current_vix=current_conditions.get("vix", 20),
            vol_analyzer=self.volatility_regime_analyzer
        )
        
        analysis["regime_impact_analysis"] = vol_impact
        
        # Exit strategy analysis
        position_details = {
            "position_value": hedge_allocation,
            "pnl_multiplier": 1.0,  # Assume break-even for new position
            "days_to_expiry": strategy.expiration_months * 30
        }
        
        exit_opportunity = strategy.evaluate_early_exit_opportunities(
            current_conditions=current_conditions,
            position_details=position_details,
            exit_manager=self.exit_strategy_manager
        )
        
        analysis["exit_strategy_analysis"] = {
            "current_exit_recommendation": {
                "recommended_exit_percentage": exit_opportunity.recommended_exit_percentage,
                "urgency_score": exit_opportunity.urgency_score,
                "trigger_type": exit_opportunity.trigger_type.value,
                "rationale": exit_opportunity.rationale
            },
            "configured_triggers": [
                {
                    "type": trigger.trigger_type.value,
                    "threshold": trigger.threshold,
                    "exit_percentage": trigger.partial_exit_percentage
                }
                for trigger in strategy.exit_triggers
            ]
        }
        
        # Historical performance simulation
        if historical_data is not None:
            performance = strategy.simulate_performance(
                historical_data=historical_data,
                portfolio_value=portfolio_value,
                exit_manager=self.exit_strategy_manager
            )
            analysis["performance_metrics"] = performance
        else:
            # Estimated performance metrics
            analysis["performance_metrics"] = {
                "annual_cost": annual_cost,
                "protection_ratio": 3.0,  # Rough estimate
                "net_annual_cost": annual_cost * 0.8  # 20% cost reduction from exits
            }
        
        # Risk assessment
        analysis["risk_assessment"] = self._assess_strategy_risks(
            strategy, current_regime, current_conditions
        )
        
        return analysis
    
    def _assess_strategy_risks(self,
                             strategy: HedgingStrategy,
                             current_regime: VolatilityRegime,
                             current_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Assess risks specific to the strategy."""
        risks = {
            "time_decay_risk": {},
            "volatility_risk": {},
            "liquidity_risk": {},
            "model_risk": {}
        }
        
        # Time decay risk
        if strategy.expiration_months <= 3:
            risks["time_decay_risk"] = {
                "level": "High",
                "description": "Short expiration increases time decay sensitivity",
                "mitigation": "Consider more frequent profit-taking"
            }
        else:
            risks["time_decay_risk"] = {
                "level": "Medium", 
                "description": "Longer expiration provides time decay buffer",
                "mitigation": "Standard monitoring sufficient"
            }
        
        # Volatility regime risk
        if current_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
            if strategy.expiration_months <= 3:
                risks["volatility_risk"] = {
                    "level": "High",
                    "description": "Short-term options expensive in high volatility regime",
                    "mitigation": "Consider extending expiration or reducing allocation"
                }
            else:
                risks["volatility_risk"] = {
                    "level": "Medium",
                    "description": "Longer-term options less affected by regime",
                    "mitigation": "Monitor for regime transitions"
                }
        else:
            risks["volatility_risk"] = {
                "level": "Low",
                "description": "Favorable volatility regime for option purchases",
                "mitigation": "Consider increasing allocation in low volatility periods"
            }
        
        return risks
    
    def _generate_relative_comparisons(self, 
                                     strategy_results: List[Tuple[HedgingStrategy, Dict]]) -> Dict[str, Any]:
        """Generate relative comparisons between strategies."""
        if len(strategy_results) < 2:
            return {"error": "Need at least 2 strategies for comparison"}
        
        comparisons = {
            "cost_efficiency_ranking": [],
            "protection_effectiveness_ranking": [],
            "regime_adaptability_ranking": [],
            "pairwise_comparisons": {}
        }
        
        # Extract key metrics for comparison
        strategy_metrics = []
        for strategy, analysis in strategy_results:
            metrics = {
                "strategy_id": strategy.strategy_id,
                "strategy_name": strategy.name,
                "annual_cost": analysis["pricing_analysis"]["annual_cost"],
                "cost_as_percentage": analysis["pricing_analysis"]["cost_as_percentage"],
                "jump_risk_premium": analysis["pricing_analysis"]["jump_risk_premium"],
                "volatility_adjustment": analysis["regime_impact_analysis"]["volatility_adjustment"],
                "cost_impact_multiplier": analysis["regime_impact_analysis"]["cost_impact_multiplier"],
                "protection_ratio": analysis["performance_metrics"].get("protection_ratio", 1.0),
                "exit_urgency": analysis["exit_strategy_analysis"]["current_exit_recommendation"]["urgency_score"]
            }
            strategy_metrics.append(metrics)
        
        # Cost efficiency ranking (lower cost = better)
        cost_ranked = sorted(strategy_metrics, key=lambda x: x["cost_as_percentage"])
        comparisons["cost_efficiency_ranking"] = [
            {
                "rank": i + 1,
                "strategy_id": item["strategy_id"],
                "strategy_name": item["strategy_name"],
                "annual_cost": item["annual_cost"],
                "cost_as_percentage": item["cost_as_percentage"]
            }
            for i, item in enumerate(cost_ranked)
        ]
        
        # Protection effectiveness ranking (higher protection ratio = better)
        protection_ranked = sorted(strategy_metrics, key=lambda x: x["protection_ratio"], reverse=True)
        comparisons["protection_effectiveness_ranking"] = [
            {
                "rank": i + 1,
                "strategy_id": item["strategy_id"],
                "strategy_name": item["strategy_name"],
                "protection_ratio": item["protection_ratio"],
                "jump_risk_premium": item["jump_risk_premium"]
            }
            for i, item in enumerate(protection_ranked)
        ]
        
        # Regime adaptability ranking (lower volatility impact = better adaptability)
        regime_ranked = sorted(strategy_metrics, key=lambda x: abs(x["volatility_adjustment"]))
        comparisons["regime_adaptability_ranking"] = [
            {
                "rank": i + 1,
                "strategy_id": item["strategy_id"], 
                "strategy_name": item["strategy_name"],
                "volatility_adjustment": item["volatility_adjustment"],
                "cost_impact_multiplier": item["cost_impact_multiplier"]
            }
            for i, item in enumerate(regime_ranked)
        ]
        
        # Pairwise comparisons
        for i, (strategy1, analysis1) in enumerate(strategy_results):
            for j, (strategy2, analysis2) in enumerate(strategy_results):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                    
                comparison_key = f"{strategy1.strategy_id}_vs_{strategy2.strategy_id}"
                
                cost1 = analysis1["pricing_analysis"]["annual_cost"]
                cost2 = analysis2["pricing_analysis"]["annual_cost"]
                protection1 = analysis1["performance_metrics"].get("protection_ratio", 1.0)
                protection2 = analysis2["performance_metrics"].get("protection_ratio", 1.0)
                
                comparisons["pairwise_comparisons"][comparison_key] = {
                    "strategy1": strategy1.name,
                    "strategy2": strategy2.name,
                    "cost_difference": cost2 - cost1,
                    "cost_difference_percentage": (cost2 - cost1) / cost1 if cost1 > 0 else 0,
                    "protection_difference": protection2 - protection1,
                    "cost_efficiency_winner": strategy1.name if cost1 < cost2 else strategy2.name,
                    "protection_winner": strategy1.name if protection1 > protection2 else strategy2.name,
                    "overall_recommendation": self._determine_pairwise_winner(
                        (strategy1, analysis1), (strategy2, analysis2)
                    )
                }
        
        return comparisons
    
    def _determine_pairwise_winner(self,
                                 strategy_pair1: Tuple[HedgingStrategy, Dict],
                                 strategy_pair2: Tuple[HedgingStrategy, Dict]) -> str:
        """Determine the better strategy in a pairwise comparison."""
        strategy1, analysis1 = strategy_pair1
        strategy2, analysis2 = strategy_pair2
        
        # Score each strategy (higher = better)
        score1 = 0
        score2 = 0
        
        # Cost efficiency (lower cost gets points)
        cost1 = analysis1["pricing_analysis"]["cost_as_percentage"]
        cost2 = analysis2["pricing_analysis"]["cost_as_percentage"]
        if cost1 < cost2:
            score1 += 2
        else:
            score2 += 2
        
        # Protection effectiveness (higher protection ratio gets points)
        protection1 = analysis1["performance_metrics"].get("protection_ratio", 1.0)
        protection2 = analysis2["performance_metrics"].get("protection_ratio", 1.0)
        if protection1 > protection2:
            score1 += 3  # Weight protection more heavily
        else:
            score2 += 3
        
        # Regime adaptability (lower volatility impact gets points)
        vol_impact1 = abs(analysis1["regime_impact_analysis"]["volatility_adjustment"])
        vol_impact2 = abs(analysis2["regime_impact_analysis"]["volatility_adjustment"])
        if vol_impact1 < vol_impact2:
            score1 += 1
        else:
            score2 += 1
        
        if score1 > score2:
            return strategy1.name
        elif score2 > score1:
            return strategy2.name
        else:
            return "Tie - context-dependent choice"
    
    def _generate_intelligent_recommendations(self,
                                            strategy_results: List[Tuple[HedgingStrategy, Dict]],
                                            current_regime: VolatilityRegime,
                                            current_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Generate intelligent recommendations based on comprehensive analysis."""
        recommendations = {
            "primary_recommendation": {},
            "regime_specific_advice": {},
            "hybrid_strategy_suggestion": {},
            "risk_warnings": [],
            "action_items": []
        }
        
        if not strategy_results:
            return {"error": "No strategies to analyze"}
        
        # Find best strategy overall
        best_strategy = None
        best_score = -float('inf')
        
        for strategy, analysis in strategy_results:
            # Calculate composite score
            cost_score = 1.0 / analysis["pricing_analysis"]["cost_as_percentage"]  # Lower cost = higher score
            protection_score = analysis["performance_metrics"].get("protection_ratio", 1.0)
            regime_score = 1.0 / (1.0 + abs(analysis["regime_impact_analysis"]["volatility_adjustment"]))
            
            composite_score = (cost_score * 0.3 + protection_score * 0.5 + regime_score * 0.2)
            
            if composite_score > best_score:
                best_score = composite_score
                best_strategy = (strategy, analysis)
        
        if best_strategy:
            strategy, analysis = best_strategy
            recommendations["primary_recommendation"] = {
                "recommended_strategy": strategy.name,
                "strategy_id": strategy.strategy_id,
                "confidence_score": min(1.0, best_score / 3.0),  # Normalize to 0-1
                "key_advantages": self._identify_strategy_advantages(strategy, analysis),
                "implementation_notes": self._generate_implementation_notes(strategy, analysis, current_regime)
            }
        
        # Regime-specific advice
        recommendations["regime_specific_advice"] = self._generate_regime_advice(
            strategy_results, current_regime, current_conditions
        )
        
        # Hybrid strategy suggestion
        if len(strategy_results) >= 2:
            recommendations["hybrid_strategy_suggestion"] = self._suggest_hybrid_strategy(
                strategy_results, current_regime
            )
        
        # Risk warnings
        recommendations["risk_warnings"] = self._generate_risk_warnings(
            strategy_results, current_regime, current_conditions
        )
        
        # Action items
        recommendations["action_items"] = self._generate_action_items(
            strategy_results, current_regime, current_conditions
        )
        
        return recommendations
    
    def _identify_strategy_advantages(self, strategy: HedgingStrategy, analysis: Dict) -> List[str]:
        """Identify key advantages of a strategy."""
        advantages = []
        
        if analysis["pricing_analysis"]["cost_as_percentage"] < 0.03:
            advantages.append("Low cost relative to portfolio value")
        
        if analysis["performance_metrics"].get("protection_ratio", 0) > 3:
            advantages.append("High protection effectiveness during stress events")
        
        if abs(analysis["regime_impact_analysis"]["volatility_adjustment"]) < 0.02:
            advantages.append("Stable cost across volatility regimes")
        
        if analysis["pricing_analysis"]["jump_risk_premium"] > 0.1:
            advantages.append("Significant tail risk protection beyond Black-Scholes")
        
        if strategy.expiration_months >= 6:
            advantages.append("Reduced transaction costs from less frequent rolling")
        
        return advantages
    
    def _generate_implementation_notes(self,
                                     strategy: HedgingStrategy,
                                     analysis: Dict,
                                     current_regime: VolatilityRegime) -> List[str]:
        """Generate implementation notes for the recommended strategy."""
        notes = []
        
        if current_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
            if strategy.expiration_months <= 3:
                notes.append("Consider delaying implementation until volatility normalizes")
            else:
                notes.append("Good timing - longer expiration avoids term structure penalty")
        
        exit_urgency = analysis["exit_strategy_analysis"]["current_exit_recommendation"]["urgency_score"]
        if exit_urgency > 0.5:
            notes.append("Set up active monitoring for exit opportunities")
        
        if analysis["pricing_analysis"]["jump_risk_premium"] > 0.15:
            notes.append("Jump risk significant - consider starting with smaller allocation")
        
        notes.append(f"Target allocation: {analysis['pricing_analysis']['cost_as_percentage']:.1%} of portfolio")
        notes.append(f"Roll positions {strategy.rolling_threshold_days} days before expiration")
        
        return notes
    
    def _generate_regime_advice(self,
                              strategy_results: List[Tuple[HedgingStrategy, Dict]],
                              current_regime: VolatilityRegime,
                              current_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Generate advice specific to current volatility regime."""
        regime_advice = {
            "current_regime": current_regime.value,
            "regime_characteristics": {},
            "optimal_strategies_for_regime": [],
            "regime_transition_guidance": {}
        }
        
        # Regime characteristics
        if current_regime == VolatilityRegime.LOW:
            regime_advice["regime_characteristics"] = {
                "description": "Low volatility environment - good time to establish hedges",
                "typical_duration": "6-18 months",
                "key_risks": "Complacency, under-hedging",
                "opportunities": "Cost-effective hedge establishment"
            }
        elif current_regime == VolatilityRegime.MEDIUM:
            regime_advice["regime_characteristics"] = {
                "description": "Transitional volatility - monitor for regime changes",
                "typical_duration": "3-6 months", 
                "key_risks": "Regime uncertainty, timing risk",
                "opportunities": "Balanced cost-protection tradeoff"
            }
        elif current_regime == VolatilityRegime.HIGH:
            regime_advice["regime_characteristics"] = {
                "description": "Elevated volatility - existing hedges likely profitable",
                "typical_duration": "1-3 months",
                "key_risks": "Term structure inversion, expensive rolling",
                "opportunities": "Profit-taking on existing positions"
            }
        else:  # EXTREME
            regime_advice["regime_characteristics"] = {
                "description": "Crisis-level volatility - focus on profit realization",
                "typical_duration": "Days to weeks",
                "key_risks": "Liquidity, extreme premium costs",
                "opportunities": "Maximum hedge effectiveness period"
            }
        
        # Find strategies best suited for current regime
        regime_scores = []
        for strategy, analysis in strategy_results:
            vol_adjustment = abs(analysis["regime_impact_analysis"]["volatility_adjustment"])
            regime_score = 1.0 / (1.0 + vol_adjustment)  # Lower adjustment = better for regime
            regime_scores.append((strategy.name, regime_score, vol_adjustment))
        
        regime_scores.sort(key=lambda x: x[1], reverse=True)
        
        regime_advice["optimal_strategies_for_regime"] = [
            {
                "strategy": name,
                "suitability_score": score,
                "volatility_impact": impact
            }
            for name, score, impact in regime_scores[:3]  # Top 3
        ]
        
        return regime_advice
    
    def _suggest_hybrid_strategy(self,
                               strategy_results: List[Tuple[HedgingStrategy, Dict]],
                               current_regime: VolatilityRegime) -> Dict[str, Any]:
        """Suggest a hybrid allocation across multiple strategies."""
        if len(strategy_results) < 2:
            return {"error": "Need at least 2 strategies for hybrid approach"}
        
        # Find complementary strategies (short-term + long-term)
        short_term_strategies = [(s, a) for s, a in strategy_results if s.expiration_months <= 3]
        long_term_strategies = [(s, a) for s, a in strategy_results if s.expiration_months >= 6]
        
        if not short_term_strategies or not long_term_strategies:
            return {"recommendation": "Consider adding both short-term and long-term strategies for diversification"}
        
        # Select best from each category
        best_short = min(short_term_strategies, 
                        key=lambda x: x[1]["pricing_analysis"]["cost_as_percentage"])
        best_long = min(long_term_strategies,
                       key=lambda x: x[1]["pricing_analysis"]["cost_as_percentage"])
        
        # Determine optimal allocation based on regime
        if current_regime == VolatilityRegime.LOW:
            short_weight = 0.3
            long_weight = 0.7
            rationale = "Favor long-term in low volatility to minimize cost"
        elif current_regime == VolatilityRegime.MEDIUM:
            short_weight = 0.5
            long_weight = 0.5
            rationale = "Balanced allocation for transitional regime"
        else:  # HIGH or EXTREME
            short_weight = 0.7
            long_weight = 0.3
            rationale = "Favor short-term for responsiveness to regime changes"
        
        # Calculate hybrid metrics
        hybrid_cost = (short_weight * best_short[1]["pricing_analysis"]["annual_cost"] + 
                      long_weight * best_long[1]["pricing_analysis"]["annual_cost"])
        
        hybrid_protection = (short_weight * best_short[1]["performance_metrics"].get("protection_ratio", 1.0) +
                           long_weight * best_long[1]["performance_metrics"].get("protection_ratio", 1.0))
        
        return {
            "hybrid_allocation": {
                "short_term_strategy": best_short[0].name,
                "short_term_weight": short_weight,
                "long_term_strategy": best_long[0].name,
                "long_term_weight": long_weight
            },
            "hybrid_metrics": {
                "blended_annual_cost": hybrid_cost,
                "blended_protection_ratio": hybrid_protection,
                "diversification_benefit": "Reduced single-strategy risk"
            },
            "rationale": rationale,
            "implementation": f"Allocate {short_weight:.0%} to {best_short[0].name} and {long_weight:.0%} to {best_long[0].name}"
        }
    
    def _generate_risk_warnings(self,
                              strategy_results: List[Tuple[HedgingStrategy, Dict]],
                              current_regime: VolatilityRegime,
                              current_conditions: Dict[str, float]) -> List[str]:
        """Generate risk warnings based on current analysis."""
        warnings = []
        
        # Check for high-cost environment
        avg_cost = np.mean([
            analysis["pricing_analysis"]["cost_as_percentage"] 
            for _, analysis in strategy_results
        ])
        
        if avg_cost > 0.05:  # 5%+ of portfolio
            warnings.append("WARNING: High hedging costs detected - consider reducing allocation or extending expiration")
        
        # Check for extreme volatility regime
        if current_regime == VolatilityRegime.EXTREME:
            warnings.append("WARNING: Extreme volatility regime - new hedge purchases may be very expensive")
        
        # Check for term structure inversion
        current_vix = current_conditions.get("vix", 20)
        if current_vix > 40:
            warnings.append("WARNING: Potential volatility term structure inversion - short-term options may be severely overpriced")
        
        # Check for liquidity concerns
        if current_conditions.get("volume_ratio", 1.0) < 0.5:
            warnings.append("WARNING: Reduced market liquidity detected - expect wider bid-ask spreads")
        
        # Check for strategy-specific risks
        for strategy, analysis in strategy_results:
            if strategy.expiration_months <= 2 and current_regime in [VolatilityRegime.HIGH, VolatilityRegime.EXTREME]:
                warnings.append(f"WARNING: {strategy.name} may be severely overpriced in current regime")
        
        return warnings
    
    def _generate_action_items(self,
                             strategy_results: List[Tuple[HedgingStrategy, Dict]],
                             current_regime: VolatilityRegime,
                             current_conditions: Dict[str, float]) -> List[str]:
        """Generate specific action items based on analysis."""
        actions = []
        
        # Check for immediate exit opportunities
        for strategy, analysis in strategy_results:
            exit_urgency = analysis["exit_strategy_analysis"]["current_exit_recommendation"]["urgency_score"]
            if exit_urgency > 0.7:
                actions.append(f"IMMEDIATE: Consider exiting {exit_urgency:.0%} of {strategy.name} positions")
        
        # Regime-specific actions
        if current_regime == VolatilityRegime.LOW:
            actions.append("Consider increasing hedge allocation while costs are low")
        elif current_regime == VolatilityRegime.EXTREME:
            actions.append("Focus on profit-taking rather than new hedge establishment")
        
        # Portfolio rebalancing
        actions.append("Review and update exit triggers based on current market conditions")
        actions.append("Set up monitoring alerts for volatility regime transitions")
        
        # Implementation actions
        actions.append("Validate option liquidity before executing large positions")
        actions.append("Consider implementing positions gradually to minimize market impact")
        
        return actions
    
    def generate_comprehensive_report(self,
                                    comparison_results: Dict[str, Any]) -> str:
        """Generate a comprehensive text report of the analysis."""
        report_sections = []
        
        # Executive Summary
        report_sections.append("# SPX Hedging Strategy Comparison Report")
        report_sections.append(f"Generated: {comparison_results['analysis_timestamp']}")
        report_sections.append(f"Portfolio Value: ${comparison_results['portfolio_value']:,.0f}")
        report_sections.append(f"Current Volatility Regime: {comparison_results['current_volatility_regime'].upper()}")
        report_sections.append("")
        
        # Primary Recommendation
        if "recommendations" in comparison_results and "primary_recommendation" in comparison_results["recommendations"]:
            rec = comparison_results["recommendations"]["primary_recommendation"]
            report_sections.append("## PRIMARY RECOMMENDATION")
            report_sections.append(f"**Strategy:** {rec['recommended_strategy']}")
            report_sections.append(f"**Confidence:** {rec['confidence_score']:.1%}")
            report_sections.append("**Key Advantages:**")
            for advantage in rec.get("key_advantages", []):
                report_sections.append(f"- {advantage}")
            report_sections.append("")
        
        # Strategy Comparison Table
        if "relative_comparisons" in comparison_results:
            report_sections.append("## STRATEGY RANKINGS")
            
            # Cost efficiency
            cost_ranking = comparison_results["relative_comparisons"].get("cost_efficiency_ranking", [])
            if cost_ranking:
                report_sections.append("### Cost Efficiency (Lower is Better)")
                for item in cost_ranking:
                    report_sections.append(f"{item['rank']}. {item['strategy_name']}: {item['cost_as_percentage']:.2%} annually")
                report_sections.append("")
            
            # Protection effectiveness
            protection_ranking = comparison_results["relative_comparisons"].get("protection_effectiveness_ranking", [])
            if protection_ranking:
                report_sections.append("### Protection Effectiveness (Higher is Better)")
                for item in protection_ranking:
                    report_sections.append(f"{item['rank']}. {item['strategy_name']}: {item['protection_ratio']:.1f}x return potential")
                report_sections.append("")
        
        # Risk Warnings
        if "recommendations" in comparison_results and "risk_warnings" in comparison_results["recommendations"]:
            warnings = comparison_results["recommendations"]["risk_warnings"]
            if warnings:
                report_sections.append("## RISK WARNINGS")
                for warning in warnings:
                    report_sections.append(f"⚠️  {warning}")
                report_sections.append("")
        
        # Action Items
        if "recommendations" in comparison_results and "action_items" in comparison_results["recommendations"]:
            actions = comparison_results["recommendations"]["action_items"]
            if actions:
                report_sections.append("## RECOMMENDED ACTIONS")
                for i, action in enumerate(actions, 1):
                    report_sections.append(f"{i}. {action}")
                report_sections.append("")
        
        return "\n".join(report_sections)