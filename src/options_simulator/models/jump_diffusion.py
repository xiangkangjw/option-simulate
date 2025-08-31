"""
Jump-Diffusion Option Pricing Models.

This module implements Merton's jump-diffusion model for more accurate 
tail risk pricing in options, particularly important for black swan events.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy.stats import norm
from scipy.optimize import minimize_scalar
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JumpDiffusionParameters:
    """Parameters for jump-diffusion model."""
    lambda_jump: float  # Jump intensity (jumps per year)
    mu_jump: float      # Mean jump size
    sigma_jump: float   # Jump volatility
    sigma_diffusion: float  # Diffusion volatility (normal Black-Scholes vol)


@dataclass
class JumpAdjustedGreeks:
    """Greeks calculated with jump-diffusion adjustments."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    jump_delta: float  # Additional delta from jump risk
    jump_gamma: float  # Additional gamma from jump risk


class JumpDiffusionPricer:
    """
    Merton Jump-Diffusion option pricing model.
    
    The model assumes that the underlying asset price follows:
    dS = μS dt + σS dW + S∫h dN(t)
    
    Where:
    - μ is the drift rate
    - σ is the diffusion volatility  
    - dW is a Wiener process
    - dN(t) is a Poisson process with intensity λ
    - h is the jump size (log-normal distribution)
    
    This is particularly important for tail hedging as it captures
    the non-continuous price jumps that occur during black swan events.
    """
    
    def __init__(self, jump_params: Optional[JumpDiffusionParameters] = None):
        """Initialize the jump-diffusion pricer."""
        self.jump_params = jump_params or self._default_jump_parameters()
        
    def _default_jump_parameters(self) -> JumpDiffusionParameters:
        """Default jump-diffusion parameters based on empirical studies."""
        return JumpDiffusionParameters(
            lambda_jump=0.1,    # ~1 jump every 10 years on average
            mu_jump=-0.05,      # Average jump is -5% (crashes more common than spikes)
            sigma_jump=0.15,    # Jump volatility of 15%
            sigma_diffusion=0.18  # Base diffusion volatility of 18%
        )
    
    def merton_jump_diffusion_price(self,
                                  S: float,      # Current stock price
                                  K: float,      # Strike price
                                  T: float,      # Time to expiration (years)
                                  r: float,      # Risk-free rate
                                  option_type: str = "put",  # "put" or "call"
                                  max_jumps: int = 50) -> float:
        """
        Calculate option price using Merton's jump-diffusion model.
        
        The price is calculated as an infinite series:
        P = Σ(n=0 to ∞) [e^(-λT) * (λT)^n / n!] * BS_price(S, K, T, r_n, σ_n)
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration in years
            r: Risk-free rate
            option_type: "put" or "call"
            max_jumps: Maximum number of jumps to consider in series
            
        Returns:
            Option price incorporating jump risk
        """
        if T <= 0:
            # Handle expiration case
            if option_type == "put":
                return max(K - S, 0)
            else:
                return max(S - K, 0)
        
        lambda_t = self.jump_params.lambda_jump
        mu_j = self.jump_params.mu_jump
        sigma_j = self.jump_params.sigma_jump
        sigma = self.jump_params.sigma_diffusion
        
        # Expected jump size
        k = np.exp(mu_j + 0.5 * sigma_j**2) - 1
        
        # Adjust risk-free rate for jump risk
        r_adjusted = r - lambda_t * k
        
        option_price = 0.0
        poisson_weights = []
        
        # Calculate series sum
        for n in range(max_jumps + 1):
            # Poisson probability for n jumps
            poisson_prob = (np.exp(-lambda_t * T) * (lambda_t * T)**n) / np.math.factorial(n)
            poisson_weights.append(poisson_prob)
            
            if poisson_prob < 1e-10:  # Negligible probability
                break
                
            # Adjusted parameters for n jumps
            if n == 0:
                # No jumps case - standard Black-Scholes
                r_n = r_adjusted
                sigma_n = sigma
            else:
                # With n jumps
                r_n = r_adjusted + n * np.log(1 + k) / T
                sigma_n = np.sqrt(sigma**2 + n * sigma_j**2 / T)
            
            # Black-Scholes price with adjusted parameters
            bs_price = self._black_scholes_price(S, K, T, r_n, sigma_n, option_type)
            option_price += poisson_prob * bs_price
            
        logger.debug(f"Jump-diffusion price: {option_price:.4f} (vs BS: {self._black_scholes_price(S, K, T, r, sigma, option_type):.4f})")
        return option_price
    
    def _black_scholes_price(self, S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
        """Standard Black-Scholes option pricing."""
        if sigma <= 0 or T <= 0:
            if option_type == "put":
                return max(K - S, 0)
            else:
                return max(S - K, 0)
                
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == "put":
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            
        return max(price, 0)  # Ensure non-negative price
    
    def calculate_jump_adjusted_greeks(self,
                                     S: float,
                                     K: float, 
                                     T: float,
                                     r: float,
                                     option_type: str = "put") -> JumpAdjustedGreeks:
        """
        Calculate Greeks with jump-diffusion adjustments.
        
        This uses numerical differentiation to calculate Greeks
        for the jump-diffusion model.
        """
        # Base price
        base_price = self.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        # Small increments for numerical differentiation
        dS = S * 0.001   # 0.1% change in stock price
        dT = 1.0 / 365   # 1 day change
        dr = 0.0001      # 1 bp change in rate
        dsigma = 0.001   # 0.1% change in volatility
        
        # Delta (∂P/∂S)
        price_up = self.merton_jump_diffusion_price(S + dS, K, T, r, option_type)
        price_down = self.merton_jump_diffusion_price(S - dS, K, T, r, option_type)
        delta = (price_up - price_down) / (2 * dS)
        
        # Gamma (∂²P/∂S²)
        gamma = (price_up - 2 * base_price + price_down) / (dS**2)
        
        # Theta (∂P/∂T) - negative because time decreases
        if T > dT:
            price_time_decay = self.merton_jump_diffusion_price(S, K, T - dT, r, option_type)
            theta = -(price_time_decay - base_price) / dT
        else:
            theta = -base_price / dT  # Approximation for very short time
            
        # Rho (∂P/∂r)
        price_rate_up = self.merton_jump_diffusion_price(S, K, T, r + dr, option_type)
        rho = (price_rate_up - base_price) / dr
        
        # Vega (∂P/∂σ) - use diffusion volatility
        original_params = self.jump_params
        
        # Increase diffusion volatility
        vol_up_params = JumpDiffusionParameters(
            lambda_jump=original_params.lambda_jump,
            mu_jump=original_params.mu_jump,
            sigma_jump=original_params.sigma_jump,
            sigma_diffusion=original_params.sigma_diffusion + dsigma
        )
        
        temp_pricer = JumpDiffusionPricer(vol_up_params)
        price_vol_up = temp_pricer.merton_jump_diffusion_price(S, K, T, r, option_type)
        vega = (price_vol_up - base_price) / dsigma
        
        # Jump-specific Greeks (additional sensitivity to jump parameters)
        # Jump Delta: sensitivity to jump intensity
        dlambda = 0.001
        jump_up_params = JumpDiffusionParameters(
            lambda_jump=original_params.lambda_jump + dlambda,
            mu_jump=original_params.mu_jump,
            sigma_jump=original_params.sigma_jump,
            sigma_diffusion=original_params.sigma_diffusion
        )
        
        temp_pricer_jump = JumpDiffusionPricer(jump_up_params)
        price_jump_up = temp_pricer_jump.merton_jump_diffusion_price(S, K, T, r, option_type)
        jump_delta = (price_jump_up - base_price) / dlambda
        
        # Jump Gamma: sensitivity to jump volatility
        dsigma_jump = 0.001
        jump_vol_params = JumpDiffusionParameters(
            lambda_jump=original_params.lambda_jump,
            mu_jump=original_params.mu_jump,
            sigma_jump=original_params.sigma_jump + dsigma_jump,
            sigma_diffusion=original_params.sigma_diffusion
        )
        
        temp_pricer_jvol = JumpDiffusionPricer(jump_vol_params)
        price_jump_vol_up = temp_pricer_jvol.merton_jump_diffusion_price(S, K, T, r, option_type)
        jump_gamma = (price_jump_vol_up - base_price) / dsigma_jump
        
        return JumpAdjustedGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            jump_delta=jump_delta,
            jump_gamma=jump_gamma
        )
    
    def calibrate_jump_parameters(self,
                                market_prices: Dict[Tuple[float, float], float],  # (K, T) -> market_price
                                S: float,
                                r: float,
                                option_type: str = "put") -> JumpDiffusionParameters:
        """
        Calibrate jump-diffusion parameters to market option prices.
        
        Args:
            market_prices: Dictionary mapping (strike, time_to_expiry) -> market_price
            S: Current stock price
            r: Risk-free rate
            option_type: Option type
            
        Returns:
            Calibrated jump-diffusion parameters
        """
        def objective_function(params_array):
            """Objective function for calibration."""
            lambda_jump, mu_jump, sigma_jump, sigma_diffusion = params_array
            
            # Ensure parameters are in reasonable bounds
            if lambda_jump < 0 or lambda_jump > 1.0:  # 0-100% jump probability per year
                return 1e10
            if sigma_jump < 0.01 or sigma_jump > 1.0:  # 1%-100% jump volatility
                return 1e10
            if sigma_diffusion < 0.05 or sigma_diffusion > 1.0:  # 5%-100% diffusion vol
                return 1e10
            if mu_jump < -0.5 or mu_jump > 0.2:  # -50% to +20% average jump
                return 1e10
                
            temp_params = JumpDiffusionParameters(
                lambda_jump=lambda_jump,
                mu_jump=mu_jump,
                sigma_jump=sigma_jump,
                sigma_diffusion=sigma_diffusion
            )
            
            temp_pricer = JumpDiffusionPricer(temp_params)
            
            total_error = 0
            for (K, T), market_price in market_prices.items():
                try:
                    model_price = temp_pricer.merton_jump_diffusion_price(S, K, T, r, option_type)
                    error = (model_price - market_price) ** 2
                    total_error += error
                except:
                    return 1e10  # Penalize parameter sets that cause errors
                    
            return total_error / len(market_prices)  # MSE
        
        # Initial guess based on default parameters
        initial_guess = [
            self.jump_params.lambda_jump,
            self.jump_params.mu_jump, 
            self.jump_params.sigma_jump,
            self.jump_params.sigma_diffusion
        ]
        
        # Parameter bounds
        bounds = [
            (0.001, 1.0),    # lambda_jump
            (-0.5, 0.2),     # mu_jump  
            (0.01, 1.0),     # sigma_jump
            (0.05, 1.0)      # sigma_diffusion
        ]
        
        try:
            from scipy.optimize import minimize
            result = minimize(
                objective_function,
                initial_guess,
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': 1000}
            )
            
            if result.success:
                calibrated_params = JumpDiffusionParameters(
                    lambda_jump=result.x[0],
                    mu_jump=result.x[1],
                    sigma_jump=result.x[2],
                    sigma_diffusion=result.x[3]
                )
                
                logger.info(f"Successfully calibrated jump-diffusion parameters: "
                          f"λ={calibrated_params.lambda_jump:.4f}, "
                          f"μ_j={calibrated_params.mu_jump:.4f}, "
                          f"σ_j={calibrated_params.sigma_jump:.4f}, "
                          f"σ={calibrated_params.sigma_diffusion:.4f}")
                
                return calibrated_params
            else:
                logger.warning("Jump-diffusion calibration failed, using default parameters")
                return self.jump_params
                
        except ImportError:
            logger.warning("SciPy not available for optimization, using default parameters")
            return self.jump_params
    
    def model_tail_event_scenarios(self,
                                 S: float,
                                 K: float, 
                                 T: float,
                                 r: float,
                                 scenario_configs: Optional[List[Dict]] = None) -> Dict[str, Dict]:
        """
        Model option pricing under different tail event scenarios.
        
        Args:
            S, K, T, r: Standard option parameters
            scenario_configs: List of scenario configurations
            
        Returns:
            Dictionary of scenarios with pricing results
        """
        scenarios = scenario_configs or self._default_tail_scenarios()
        results = {}
        
        for scenario in scenarios:
            scenario_name = scenario["name"]
            scenario_params = JumpDiffusionParameters(
                lambda_jump=scenario["lambda_jump"],
                mu_jump=scenario["mu_jump"], 
                sigma_jump=scenario["sigma_jump"],
                sigma_diffusion=scenario["sigma_diffusion"]
            )
            
            temp_pricer = JumpDiffusionPricer(scenario_params)
            
            put_price = temp_pricer.merton_jump_diffusion_price(S, K, T, r, "put")
            call_price = temp_pricer.merton_jump_diffusion_price(S, K, T, r, "call")
            
            # Calculate standard Black-Scholes for comparison
            bs_put = self._black_scholes_price(S, K, T, r, scenario_params.sigma_diffusion, "put")
            bs_call = self._black_scholes_price(S, K, T, r, scenario_params.sigma_diffusion, "call")
            
            results[scenario_name] = {
                "jump_diffusion_put": put_price,
                "jump_diffusion_call": call_price,
                "black_scholes_put": bs_put,
                "black_scholes_call": bs_call,
                "put_premium": (put_price - bs_put) / bs_put if bs_put > 0 else 0,
                "call_premium": (call_price - bs_call) / bs_call if bs_call > 0 else 0,
                "scenario_parameters": scenario_params
            }
            
        return results
    
    def _default_tail_scenarios(self) -> List[Dict]:
        """Default tail event scenarios for modeling."""
        return [
            {
                "name": "Normal Market",
                "lambda_jump": 0.05,    # Low jump frequency
                "mu_jump": -0.02,       # Small average decline
                "sigma_jump": 0.10,     # Moderate jump volatility
                "sigma_diffusion": 0.18
            },
            {
                "name": "Moderate Stress",
                "lambda_jump": 0.15,    # Increased jump frequency
                "mu_jump": -0.05,       # Larger average decline
                "sigma_jump": 0.15,     # Higher jump volatility
                "sigma_diffusion": 0.22
            },
            {
                "name": "High Stress",
                "lambda_jump": 0.25,    # High jump frequency
                "mu_jump": -0.08,       # Significant average decline
                "sigma_jump": 0.20,     # High jump volatility
                "sigma_diffusion": 0.30
            },
            {
                "name": "Crisis Mode",
                "lambda_jump": 0.50,    # Very high jump frequency
                "mu_jump": -0.12,       # Large average decline  
                "sigma_jump": 0.30,     # Extreme jump volatility
                "sigma_diffusion": 0.45
            }
        ]
    
    def assess_jump_risk_premium(self,
                               S: float,
                               K: float,
                               T: float, 
                               r: float,
                               option_type: str = "put") -> Dict[str, float]:
        """
        Assess the risk premium associated with jump risk.
        
        Returns the additional premium that jump-diffusion pricing
        adds compared to standard Black-Scholes pricing.
        """
        # Jump-diffusion price
        jd_price = self.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        # Black-Scholes price with same diffusion volatility
        bs_price = self._black_scholes_price(S, K, T, r, 
                                           self.jump_params.sigma_diffusion, option_type)
        
        # Risk premiums
        absolute_premium = jd_price - bs_price
        relative_premium = (absolute_premium / bs_price) if bs_price > 0 else 0
        
        # Decompose premium by jump characteristics
        lambda_contrib = self._calculate_lambda_contribution(S, K, T, r, option_type)
        jump_size_contrib = self._calculate_jump_size_contribution(S, K, T, r, option_type)
        
        return {
            "jump_diffusion_price": jd_price,
            "black_scholes_price": bs_price,
            "absolute_risk_premium": absolute_premium,
            "relative_risk_premium": relative_premium,
            "jump_frequency_contribution": lambda_contrib,
            "jump_size_contribution": jump_size_contrib,
            "total_jump_risk_score": relative_premium  # 0-1 scale, higher = more jump risk
        }
    
    def _calculate_lambda_contribution(self, S, K, T, r, option_type):
        """Calculate contribution of jump frequency to risk premium."""
        # Price with no jumps
        no_jump_params = JumpDiffusionParameters(
            lambda_jump=0.0,
            mu_jump=self.jump_params.mu_jump,
            sigma_jump=self.jump_params.sigma_jump,
            sigma_diffusion=self.jump_params.sigma_diffusion
        )
        
        no_jump_pricer = JumpDiffusionPricer(no_jump_params)
        no_jump_price = no_jump_pricer.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        # Current price
        current_price = self.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        return current_price - no_jump_price
    
    def _calculate_jump_size_contribution(self, S, K, T, r, option_type):
        """Calculate contribution of jump size to risk premium."""
        # Price with small jumps
        small_jump_params = JumpDiffusionParameters(
            lambda_jump=self.jump_params.lambda_jump,
            mu_jump=0.0,  # No average jump
            sigma_jump=0.05,  # Very small jump volatility
            sigma_diffusion=self.jump_params.sigma_diffusion
        )
        
        small_jump_pricer = JumpDiffusionPricer(small_jump_params)
        small_jump_price = small_jump_pricer.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        # Current price
        current_price = self.merton_jump_diffusion_price(S, K, T, r, option_type)
        
        return current_price - small_jump_price
    
    def generate_jump_diffusion_report(self,
                                     S: float,
                                     strikes: List[float],
                                     expirations: List[float],
                                     r: float) -> Dict:
        """
        Generate comprehensive jump-diffusion analysis report.
        
        Args:
            S: Current stock price
            strikes: List of strike prices to analyze
            expirations: List of expiration times (years) 
            r: Risk-free rate
            
        Returns:
            Comprehensive jump-diffusion report
        """
        report = {
            "model_parameters": {
                "lambda_jump": self.jump_params.lambda_jump,
                "mu_jump": self.jump_params.mu_jump,
                "sigma_jump": self.jump_params.sigma_jump,
                "sigma_diffusion": self.jump_params.sigma_diffusion
            },
            "pricing_analysis": {},
            "greeks_analysis": {},
            "risk_premium_analysis": {},
            "scenario_analysis": {}
        }
        
        # Analyze pricing for different strikes and expirations
        for T in expirations:
            expiry_key = f"{int(T*365)}d"
            report["pricing_analysis"][expiry_key] = {}
            report["greeks_analysis"][expiry_key] = {}
            report["risk_premium_analysis"][expiry_key] = {}
            
            for K in strikes:
                otm_pct = (K - S) / S
                strike_key = f"{otm_pct:.1%}_OTM"
                
                # Pricing analysis
                jd_put = self.merton_jump_diffusion_price(S, K, T, r, "put")
                bs_put = self._black_scholes_price(S, K, T, r, self.jump_params.sigma_diffusion, "put")
                
                report["pricing_analysis"][expiry_key][strike_key] = {
                    "jump_diffusion_price": jd_put,
                    "black_scholes_price": bs_put,
                    "price_ratio": jd_put / bs_put if bs_put > 0 else 0
                }
                
                # Greeks analysis
                greeks = self.calculate_jump_adjusted_greeks(S, K, T, r, "put")
                report["greeks_analysis"][expiry_key][strike_key] = {
                    "delta": greeks.delta,
                    "gamma": greeks.gamma,
                    "theta": greeks.theta,
                    "vega": greeks.vega,
                    "jump_delta": greeks.jump_delta,
                    "jump_gamma": greeks.jump_gamma
                }
                
                # Risk premium analysis
                risk_premium = self.assess_jump_risk_premium(S, K, T, r, "put")
                report["risk_premium_analysis"][expiry_key][strike_key] = risk_premium
        
        # Scenario analysis
        scenario_results = self.model_tail_event_scenarios(
            S, strikes[0], expirations[0], r  # Use first strike/expiry for scenario analysis
        )
        report["scenario_analysis"] = scenario_results
        
        # Summary insights
        avg_risk_premium = np.mean([
            analysis["relative_risk_premium"] 
            for expiry_data in report["risk_premium_analysis"].values()
            for analysis in expiry_data.values()
        ])
        
        report["summary"] = {
            "average_risk_premium": avg_risk_premium,
            "jump_risk_significance": "High" if avg_risk_premium > 0.2 else "Medium" if avg_risk_premium > 0.1 else "Low",
            "model_recommendation": self._generate_model_recommendation(avg_risk_premium)
        }
        
        return report
    
    def _generate_model_recommendation(self, avg_risk_premium: float) -> str:
        """Generate recommendation based on jump risk analysis."""
        if avg_risk_premium > 0.3:
            return "Jump risk is significant. Consider using jump-diffusion pricing for all tail hedging analysis."
        elif avg_risk_premium > 0.15:
            return "Moderate jump risk detected. Jump-diffusion pricing recommended for OTM options."
        elif avg_risk_premium > 0.05:
            return "Low jump risk. Black-Scholes adequate for most cases, but consider jump-diffusion for stress testing."
        else:
            return "Minimal jump risk detected. Standard Black-Scholes pricing should be sufficient."