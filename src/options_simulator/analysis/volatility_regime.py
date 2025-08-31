"""
Volatility Regime Analysis for Tail Hedging Strategies.

This module analyzes market volatility regimes and their impact on options pricing,
particularly focusing on term structure dynamics during market stress periods.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VolatilityRegime(Enum):
    """Volatility regime classifications based on VIX levels."""
    LOW = "low"          # VIX < 15
    MEDIUM = "medium"    # 15 <= VIX < 25  
    HIGH = "high"        # 25 <= VIX < 40
    EXTREME = "extreme"  # VIX >= 40


@dataclass
class TermStructurePoint:
    """Represents a point on the volatility term structure."""
    days_to_expiry: int
    implied_volatility: float
    strike: float
    regime: VolatilityRegime


@dataclass
class RegimeAnalysis:
    """Results of volatility regime analysis."""
    current_regime: VolatilityRegime
    regime_probability: float
    term_structure_inversion: bool
    short_term_premium: float  # Premium for short-term options relative to long-term
    transition_probability: Dict[VolatilityRegime, float]
    recommended_allocation_adjustment: float  # Multiplier for base allocation


class VolatilityRegimeAnalyzer:
    """
    Analyzes volatility regimes and their impact on options pricing strategies.
    
    Key Functionality:
    1. Classifies current market volatility regime
    2. Models term structure dynamics during stress
    3. Calculates relative pricing efficiency between expirations
    4. Recommends dynamic allocation adjustments
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the volatility regime analyzer."""
        self.config = config or self._default_config()
        self._regime_history: List[Tuple[pd.Timestamp, VolatilityRegime]] = []
        
    def _default_config(self) -> Dict:
        """Default configuration for volatility regime analysis."""
        return {
            # Regime thresholds
            "vix_thresholds": {
                VolatilityRegime.LOW: 15,
                VolatilityRegime.MEDIUM: 25, 
                VolatilityRegime.HIGH: 40,
                VolatilityRegime.EXTREME: 60
            },
            
            # Term structure parameters
            "reference_expirations": [30, 60, 90, 180],  # days
            "inversion_threshold": 0.05,  # 5% higher short-term vol indicates inversion
            
            # Regime transition parameters  
            "persistence_factor": 0.8,  # How sticky regimes are
            "mean_reversion_speed": 0.1,  # Speed of regime mean reversion
            
            # Allocation adjustment multipliers by regime
            "allocation_multipliers": {
                VolatilityRegime.LOW: 1.0,
                VolatilityRegime.MEDIUM: 1.3,
                VolatilityRegime.HIGH: 1.8,
                VolatilityRegime.EXTREME: 2.5
            }
        }
    
    def classify_current_regime(self, vix_level: float, 
                              historical_vix: Optional[pd.Series] = None) -> VolatilityRegime:
        """
        Classify the current volatility regime based on VIX level.
        
        Args:
            vix_level: Current VIX level
            historical_vix: Historical VIX data for context
            
        Returns:
            Current volatility regime
        """
        thresholds = self.config["vix_thresholds"]
        
        if vix_level < thresholds[VolatilityRegime.LOW]:
            regime = VolatilityRegime.LOW
        elif vix_level < thresholds[VolatilityRegime.MEDIUM]:
            regime = VolatilityRegime.MEDIUM
        elif vix_level < thresholds[VolatilityRegime.HIGH]:
            regime = VolatilityRegime.HIGH
        else:
            regime = VolatilityRegime.EXTREME
            
        # Store in history for transition analysis
        self._regime_history.append((pd.Timestamp.now(), regime))
        
        logger.info(f"Classified volatility regime: {regime.value} (VIX: {vix_level:.2f})")
        return regime
    
    def model_term_structure_dynamics(self, current_vix: float,
                                    historical_surface: Optional[pd.DataFrame] = None) -> Dict[int, float]:
        """
        Model how volatility term structure changes across regimes.
        
        During market stress, term structure often inverts with short-term vol > long-term vol.
        This is critical for understanding when 2-month puts become expensive vs 6-month puts.
        
        Args:
            current_vix: Current VIX level
            historical_surface: Historical volatility surface data
            
        Returns:
            Dict mapping days to expiry -> expected implied volatility adjustment
        """
        regime = self.classify_current_regime(current_vix)
        expirations = self.config["reference_expirations"]
        
        # Base term structure (normal market conditions)
        # Typically decreasing: short-term > medium-term > long-term (slight downward slope)
        base_adjustments = {
            30: 0.02,   # +2% for 1-month
            60: 0.00,   # baseline for 2-month  
            90: -0.01,  # -1% for 3-month
            180: -0.02  # -2% for 6-month
        }
        
        # Regime-specific adjustments
        if regime == VolatilityRegime.LOW:
            # Normal term structure, slight downward slope
            regime_adjustments = {30: 0, 60: 0, 90: 0, 180: 0}
            
        elif regime == VolatilityRegime.MEDIUM:
            # Slight steepening, short-term vol picks up
            regime_adjustments = {30: 0.03, 60: 0.01, 90: 0, 180: -0.01}
            
        elif regime == VolatilityRegime.HIGH:
            # Significant inversion: short-term vol spikes dramatically
            regime_adjustments = {30: 0.10, 60: 0.05, 90: 0.02, 180: 0}
            
        else:  # EXTREME
            # Severe inversion: extreme premium on short-term options
            regime_adjustments = {30: 0.20, 60: 0.12, 90: 0.06, 180: 0.02}
        
        # Combine base and regime adjustments
        final_adjustments = {}
        for expiry in expirations:
            final_adjustments[expiry] = base_adjustments[expiry] + regime_adjustments[expiry]
            
        logger.info(f"Term structure adjustments for {regime.value} regime: {final_adjustments}")
        return final_adjustments
    
    def calculate_regime_transition_probabilities(self, 
                                                current_regime: VolatilityRegime,
                                                forecast_horizon_days: int = 30) -> Dict[VolatilityRegime, float]:
        """
        Calculate probabilities of transitioning to different volatility regimes.
        
        Args:
            current_regime: Current volatility regime
            forecast_horizon_days: Forecast horizon in days
            
        Returns:
            Dict mapping regime -> transition probability
        """
        # Transition matrix based on historical regime persistence
        # Rows = current regime, Columns = next regime
        base_transition_matrix = {
            VolatilityRegime.LOW: {
                VolatilityRegime.LOW: 0.85,
                VolatilityRegime.MEDIUM: 0.12,
                VolatilityRegime.HIGH: 0.03,
                VolatilityRegime.EXTREME: 0.00
            },
            VolatilityRegime.MEDIUM: {
                VolatilityRegime.LOW: 0.20,
                VolatilityRegime.MEDIUM: 0.60,
                VolatilityRegime.HIGH: 0.18,
                VolatilityRegime.EXTREME: 0.02
            },
            VolatilityRegime.HIGH: {
                VolatilityRegime.LOW: 0.05,
                VolatilityRegime.MEDIUM: 0.25,
                VolatilityRegime.HIGH: 0.60,
                VolatilityRegime.EXTREME: 0.10
            },
            VolatilityRegime.EXTREME: {
                VolatilityRegime.LOW: 0.01,
                VolatilityRegime.MEDIUM: 0.09,
                VolatilityRegime.HIGH: 0.50,
                VolatilityRegime.EXTREME: 0.40
            }
        }
        
        # Adjust for forecast horizon (longer horizons = more mean reversion)
        horizon_adjustment = min(1.0, forecast_horizon_days / 30.0)
        transition_probs = base_transition_matrix[current_regime].copy()
        
        # Apply mean reversion for longer horizons
        if horizon_adjustment > 0.5:
            mean_reversion_factor = (horizon_adjustment - 0.5) * 0.3
            # Increase probability of reverting to medium regime
            medium_boost = mean_reversion_factor * 0.2
            transition_probs[VolatilityRegime.MEDIUM] += medium_boost
            
            # Normalize to ensure probabilities sum to 1
            total = sum(transition_probs.values())
            transition_probs = {k: v/total for k, v in transition_probs.items()}
        
        return transition_probs
    
    def assess_relative_pricing_efficiency(self, short_term_expiry: int = 60,
                                         long_term_expiry: int = 180,
                                         current_regime: Optional[VolatilityRegime] = None) -> float:
        """
        Assess relative pricing efficiency between short-term and long-term options.
        
        Returns the "premium" that short-term options carry relative to long-term options.
        Values > 1.0 indicate short-term options are expensive relative to long-term.
        
        Args:
            short_term_expiry: Days to expiry for short-term option (default: 2 months)
            long_term_expiry: Days to expiry for long-term option (default: 6 months) 
            current_regime: Current volatility regime
            
        Returns:
            Relative pricing ratio (short_term_cost / long_term_cost per unit time)
        """
        if current_regime is None:
            # Assume medium regime if not specified
            current_regime = VolatilityRegime.MEDIUM
            
        # Get term structure adjustments
        term_adjustments = self.model_term_structure_dynamics(25.0)  # Example VIX level
        
        # Calculate time-adjusted relative pricing
        short_vol_adjustment = term_adjustments.get(short_term_expiry, 0)
        long_vol_adjustment = term_adjustments.get(long_term_expiry, 0)
        
        # Base volatility level
        base_vol = 0.20  # 20% base volatility
        
        # Adjusted volatilities
        short_vol = base_vol + short_vol_adjustment
        long_vol = base_vol + long_vol_adjustment
        
        # Rough approximation: option price proportional to vol * sqrt(time)
        short_cost_per_day = short_vol * np.sqrt(short_term_expiry) / short_term_expiry
        long_cost_per_day = long_vol * np.sqrt(long_term_expiry) / long_term_expiry
        
        relative_efficiency = short_cost_per_day / long_cost_per_day
        
        logger.info(f"Relative pricing efficiency ({short_term_expiry}d vs {long_term_expiry}d): {relative_efficiency:.3f}")
        return relative_efficiency
    
    def recommend_dynamic_allocation_adjustments(self, 
                                               current_regime: VolatilityRegime,
                                               base_allocation: float = 0.05) -> Dict[str, float]:
        """
        Recommend dynamic allocation adjustments based on volatility regime.
        
        Args:
            current_regime: Current volatility regime
            base_allocation: Base allocation percentage (e.g., 5%)
            
        Returns:
            Dict with recommended adjustments
        """
        multiplier = self.config["allocation_multipliers"][current_regime]
        relative_efficiency = self.assess_relative_pricing_efficiency(
            current_regime=current_regime
        )
        
        # Adjust allocation based on both regime and pricing efficiency
        # If short-term options are very expensive, reduce allocation or shift to longer-term
        efficiency_adjustment = 1.0
        if relative_efficiency > 1.5:
            efficiency_adjustment = 0.8  # Reduce allocation if short-term is very expensive
        elif relative_efficiency > 2.0:
            efficiency_adjustment = 0.6  # Significant reduction
            
        final_multiplier = multiplier * efficiency_adjustment
        adjusted_allocation = base_allocation * final_multiplier
        
        recommendations = {
            "regime": current_regime.value,
            "base_allocation": base_allocation,
            "regime_multiplier": multiplier,
            "efficiency_adjustment": efficiency_adjustment,
            "final_multiplier": final_multiplier,
            "recommended_allocation": adjusted_allocation,
            "shift_to_longer_term": relative_efficiency > 1.8
        }
        
        logger.info(f"Allocation recommendation: {recommendations}")
        return recommendations
    
    def analyze_volatility_surface_changes(self, 
                                         historical_surfaces: Optional[List[pd.DataFrame]] = None) -> Dict[str, float]:
        """
        Analyze how volatility surfaces change across different market regimes.
        
        This is crucial for understanding the impact on multi-expiration hedging strategies.
        """
        # Placeholder for volatility surface analysis
        # In a full implementation, this would analyze:
        # 1. Skew changes across strikes
        # 2. Term structure evolution
        # 3. Surface stability across regimes
        
        return {
            "skew_steepness": 0.15,  # Put skew steepness
            "term_structure_slope": -0.02,  # Typical downward sloping term structure
            "surface_stability": 0.75,  # Stability score (0-1)
            "regime_impact_factor": 1.25  # How much regime changes affect pricing
        }
    
    def compute_term_structure_inversion_impact(self, 
                                              target_expirations: List[int]) -> Dict[int, float]:
        """
        Compute the impact of term structure inversion on different expiration strategies.
        
        Args:
            target_expirations: List of target expirations in days
            
        Returns:
            Dict mapping expiration -> cost impact multiplier
        """
        # Get current term structure dynamics
        term_adjustments = self.model_term_structure_dynamics(current_vix=30.0)
        
        impact_multipliers = {}
        base_expiry = 90  # 3-month reference point
        
        for expiry in target_expirations:
            if expiry in term_adjustments:
                adjustment = term_adjustments[expiry]
                base_adjustment = term_adjustments.get(base_expiry, 0)
                
                # Convert volatility adjustment to approximate cost impact
                # Higher vol = higher option prices (roughly linear for ATM options)
                cost_impact = 1.0 + (adjustment - base_adjustment)
                impact_multipliers[expiry] = cost_impact
            else:
                # Interpolate for non-standard expirations
                impact_multipliers[expiry] = 1.0
                
        return impact_multipliers
    
    def generate_regime_report(self, current_vix: float) -> Dict[str, any]:
        """
        Generate a comprehensive regime analysis report.
        
        Args:
            current_vix: Current VIX level
            
        Returns:
            Comprehensive regime analysis report
        """
        current_regime = self.classify_current_regime(current_vix)
        transition_probs = self.calculate_regime_transition_probabilities(current_regime)
        term_structure = self.model_term_structure_dynamics(current_vix)
        allocation_recs = self.recommend_dynamic_allocation_adjustments(current_regime)
        pricing_efficiency = self.assess_relative_pricing_efficiency(current_regime=current_regime)
        
        report = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "current_vix": current_vix,
            "current_regime": current_regime.value,
            "regime_analysis": {
                "transition_probabilities": {k.value: v for k, v in transition_probs.items()},
                "persistence_probability": transition_probs[current_regime]
            },
            "term_structure_analysis": {
                "adjustments_by_expiry": term_structure,
                "inversion_detected": term_structure[30] > term_structure[180],
                "short_term_premium": term_structure[60] - term_structure[180]
            },
            "pricing_efficiency": {
                "relative_efficiency_2m_vs_6m": pricing_efficiency,
                "short_term_expensive": pricing_efficiency > 1.5
            },
            "allocation_recommendations": allocation_recs
        }
        
        return report