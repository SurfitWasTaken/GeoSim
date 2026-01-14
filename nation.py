"""
Configuration and constants for realistic geopolitical simulation.
Parameters calibrated to empirical data and established economic models.
"""

from typing import Dict, List, Set, Tuple, Optional
import random
import numpy as np

# use canonical shared config/constants to avoid duplication / circular imports
from config import SimulationConfig, GOVERNMENT_TYPES, NATION_NAME_PARTS


class Currency:
    """
    Currency model supporting multiple regimes: Floating, Gold Standard, Pegged.
    """
    def __init__(self, name: str, exchange_rate: float = 1.0, regime: str = "floating"):
        self.name = name
        self.exchange_rate = float(exchange_rate)
        self.interest_rate = 0.01  # policy rate
        self.reserves = 0.0
        
        # New regime fields
        self.regime = regime  # "floating", "gold", "pegged"
        self.peg_target: Optional[float] = None  # Target rate if pegged
        self.gold_reserves: float = 0.0  # For gold standard
        
    def update_exchange_rate(self, bop: float, inflation_diff: float, config) -> None:
        """
        Update exchange rate based on regime.
        """
        if self.regime == "gold":
            # Fixed rate, but reserves drain with deficits
            reserve_drain = abs(bop) * 0.1
            if bop < 0:
                self.gold_reserves -= reserve_drain
            else:
                self.gold_reserves += reserve_drain
                
            # Crisis trigger: run out of gold -> forced devaluation
            if self.gold_reserves < 0:
                self.regime = "floating"
                self.exchange_rate *= 0.7  # 30% devaluation shock
                self.gold_reserves = 0.0
                
        elif self.regime == "pegged":
            # Maintain peg but vulnerable to speculative attacks
            if abs(bop) > 0.1:  # Large imbalance
                attack_prob = 0.2
                if random.random() < attack_prob:
                    # Currency crisis / Broken peg
                    self.regime = "floating"
                    self.exchange_rate *= 0.5  # 50% crash
            # If peg holds, rate stays (mostly) fixed, small noise
            noise = random.gauss(0, 0.001)
            self.exchange_rate *= (1 + noise)
            
        else:
            # Floating: Geometric Brownian Motion-like
            # dS = mu*S*dt + sigma*S*dW
            # Drift driven by BOP and inflation differential
            drift = bop * 0.1 - inflation_diff * 0.5
            volatility = config.exchange_rate_volatility
            noise = random.gauss(0, volatility)
            
            self.exchange_rate *= (1 + drift + noise)
            
        # keep sane bounds
        self.exchange_rate = max(0.001, min(1000.0, self.exchange_rate))


class Nation:
    """Model of a sovereign nation used by world, economy, events, combat, etc."""
    def __init__(
        self,
        id: int,
        name: str,
        government_type: str,
        population: float,
        gdp: float,
        technology: float,
        military_power: Dict[str, float],
        health: float,
        ideology: float,
        stability: float,
        currency: Currency,
    ):
        # identity
        self.id = int(id)
        self.name = name

        # basic attributes
        self.government_type = government_type
        self.population = float(population)
        self.gdp = float(gdp)
        self.technology = float(technology)
        self.military_power = dict(military_power)
        self.health = float(health)
        self.ideology = float(ideology)
        
        # Initialize previous state variables to prevent runtime errors
        self._prev_gdp_election = self.gdp
        self._prev_gdp_debt = self.gdp
        self.stability = float(stability)
        self.currency = currency
        self.budget: Dict[str, float] = {"military": 0.02, "research": 0.03, "welfare": 0.10} # % of GDP

        # dynamic / bookkeeping fields expected elsewhere
        self.alliances: Set[int] = set()
        self.relations_with: Dict[int, float] = {} # Diplomatic relations -100 to 100
        self.trade_balance: float = 0.0
        self.fdi_inflows: float = 0.0
        self.fdi_outflows: float = 0.0
        self.fdi_positions: Dict[int, float] = {}  # Bilateral FDI stocks {target_id: amount}
        self.debt_to_gdp: float = 0.0
        self.inflation_rate: float = 0.02
        self.is_at_war: bool = False
        self.war_exhaustion: float = 0.0

        self.territory_tiles: List[Tuple[int, int]] = []
        self.is_coastal: bool = True  # Default to true, updated by world gen
        self.resources: Dict[str, float] = {}
        
        # Demographics
        # 0-14, 15-64, 65+
        self.age_distribution = {"youth": 0.25, "working": 0.65, "elderly": 0.10}
        
        # Crisis Tracking
        self.crisis_active = False
        self.crisis_duration = 0
        self.months_since_crisis = 0
        self.resources_extracted: Dict[str, float] = {} # Track extraction for Hubbert curve
        self.resources_initial: Dict[str, float] = {} # Track initial for Hubbert curve
        
        # Initialize Sub-Systems
        # Deferred import to avoid circular dependency
        from politics import PoliticalSystem
        from intelligence import SpyAgency
        
        self.politics = PoliticalSystem(self)
        self.intelligence = SpyAgency(self)
        
        # Sanctions tracking
        self.sanctions_active: Set[int] = set() # Nations we are sanctioning
        self.sanctions_from: Set[int] = set()   # Nations sanctioning us
        
        self.last_election: int = -999
        self.pandemic_active: bool = False
        self.has_space_program: bool = False

        self.colonial_subjects: Set[int] = set()
        self.colonial_influence: float = 0.0

        # private previous-step trackers used by some systems
        # private previous-step trackers used by some systems
        # (Already initialized above)
        
        # New Economic Fields for Cobb-Douglas
        self.capital_stock = self.gdp * 3.0  # Initial estimate (K/Y ~ 3)
        self.investment_rate = 0.25  # Default 25% investment rate

    # --- utility / API methods used across modules/tests ---

    def get_total_military_power(self) -> float:
        """Return simple aggregate military power used by combat/economy heuristics."""
        return sum(self.military_power.get(k, 0) for k in ("army", "navy", "air", "nuclear"))

    def calculate_gdp(self, config, global_trade_multiplier: float = 1.0) -> float:
        """
        Cobb-Douglas Production Function: Y = A * K^alpha * L^(1-alpha)
        Enhanced with Human Capital and Demographics.
        """
        # 1. Human Capital (h)
        # Health and Education (proxied by Tech) boost productivity
        h = (self.health / 100.0) * (1 + self.technology / 200.0)
        
        # 2. Effective Labor (L)
        # Demographics: Higher tech -> Aging population -> Lower working age ratio
        working_age_ratio = 0.65 - (self.technology / 1000.0)
        L_effective = self.population * working_age_ratio * h
        L_millions = max(1.0, L_effective / 1e6)
        
        # 3. Total Factor Productivity (A)
        # Institutions (Stability) and Technology
        # Base TFP = 1.0 + growth_factor
        tfp_base = 1.0 + (config.tfp_growth_base * config.get_realism_multiplier())
        # Tech multiplier
        tfp_tech = 1 + self.technology / 100.0
        
        A_institutions = (self.stability / 100.0) * 1.2
        scaling_factor = 0.05 # Calibrated
        A = tfp_base * tfp_tech * A_institutions * scaling_factor
        
        # 4. Capital (K)
        K = max(1.0, self.capital_stock)
        K_trillions = max(0.001, K / 1e12)
        
        alpha = config.capital_share_alpha
        
        # 5. Production
        raw_gdp_trillions = A * (K_trillions ** alpha) * (L_millions ** (1 - alpha))
        raw_gdp = raw_gdp_trillions * 1e12
        
        # 6. Apply External Factors
        new_gdp = raw_gdp * global_trade_multiplier
        if self.is_at_war:
            new_gdp *= 0.92  # War damage
            
        # 7. Capital Accumulation & Convergence
        # Solow model: K_next = K + Investment - Depreciation
        
        # Convergence check: If K/Y ratio is too high, investment efficiency drops
        k_ratio = self.capital_stock / max(1.0, new_gdp)
        effective_investment_rate = self.investment_rate
        if k_ratio > 5.0:
            effective_investment_rate *= 0.95 # Diminishing returns to investment
            
        investment = new_gdp * effective_investment_rate
        depreciation = K * config.depreciation_rate
        self.capital_stock = max(1.0, K + investment - depreciation)
        
        # Safety bounds
        new_gdp = max(config.gdp_min, min(config.gdp_max, new_gdp))
            
        self.gdp = float(new_gdp)
        return self.gdp

    def manage_monetary_policy(self, config):
        """
        Central Bank sets interest rates using Taylor Rule.
        i = r* + pi + 0.5(pi - pi*) + 0.5(y - y*)
        """
        if self.currency.regime == "pegged":
            return

        # Target inflation
        pi_star = config.base_inflation_target
        
        # Current inflation
        pi = self.inflation_rate
        
        # Output gap (y - y*)
        # Estimate potential GDP using simplified trend or capacity
        # Here we use recent growth deviation or just assume potential is close to current
        # Simplified: Output gap is positive if growth is high (>3%), negative if low (<1%)
        prev_gdp = getattr(self, "_prev_gdp_election", self.gdp * 0.98) # Fallback
        growth = (self.gdp / max(1, prev_gdp)) - 1
        output_gap = growth - 0.02 # Assume 2% is potential growth
        
        # Taylor Rule
        r_star = 0.02 # Neutral real rate
        
        target_rate = r_star + pi + 0.5 * (pi - pi_star) + 0.5 * output_gap
        
        # Smoothing (Central banks don't move instantly)
        current_rate = self.currency.interest_rate
        new_rate = current_rate * 0.8 + target_rate * 0.2
        
        # Zero Lower Bound (mostly)
        self.currency.interest_rate = max(0.0, new_rate)

    def _calculate_age_structure(self):
        """
        Update age distribution based on development level.
        High tech/health -> Aging population.
        """
        # Demographic transition model
        development_score = (self.technology + self.health) / 200.0
        
        # Target distributions
        # Low dev: 40% youth, 55% working, 5% elderly
        # High dev: 15% youth, 60% working, 25% elderly
        
        target_youth = 0.40 - (0.25 * development_score)
        target_elderly = 0.05 + (0.20 * development_score)
        target_working = 1.0 - target_youth - target_elderly
        
        # Slow transition
        self.age_distribution["youth"] = self.age_distribution["youth"] * 0.95 + target_youth * 0.05
        self.age_distribution["working"] = self.age_distribution["working"] * 0.95 + target_working * 0.05
        self.age_distribution["elderly"] = self.age_distribution["elderly"] * 0.95 + target_elderly * 0.05
        
        # Ensure sum is 1 and values are non-negative
        total = sum(self.age_distribution.values())
        for key in self.age_distribution:
            self.age_distribution[key] /= total
            self.age_distribution[key] = max(0.0, self.age_distribution[key])

    def invest_rd(self, rd_fraction: float, config) -> None:
        """
        Invest a fraction of GDP into R&D -> increases technology.
        rd_fraction is fraction of GDP (e.g. 0.03 for 3%).
        """
        rd_spend = rd_fraction * self.gdp
        tech_gain = (rd_spend / max(1.0, self.gdp)) * config.tech_rd_efficiency * 100.0
        # Diminishing returns
        self.technology = min(100.0, self.technology + tech_gain)

    def build_military(self, spending_fraction: float, config) -> None:
        """
        Convert a fraction of GDP into military power increases.
        Distribute increases across branches; cost scales with military_gdp_cost.
        """
        spending = spending_fraction * self.gdp
        # convert spending into "power" loosely
        power_units = spending / (self.gdp * config.military_gdp_cost + 1e-12) * 0.001
        # distribute
        self.military_power["army"] = self.military_power.get("army", 0) + power_units * 0.5
        self.military_power["navy"] = self.military_power.get("navy", 0) + power_units * 0.25
        self.military_power["air"] = self.military_power.get("air", 0) + power_units * 0.25
        # nuclear not cheaply built here

    def update_health(self, config) -> None:
        """Update health index slowly based on GDP per capita and tech."""
        try:
            gdp_pc = self.get_gdp_per_capita()
            delta = (gdp_pc / 50000.0) * config.health_gdp_elasticity + (self.technology / 100.0) * config.health_tech_bonus
            # small adjustment
            self.health = float(max(config.health_min, min(config.health_max, self.health + (delta - 0.01))))
        except Exception:
            pass

    def update_population(self, config) -> None:
        """Logistic-ish population update using base growth and carrying capacity."""
        base = config.pop_growth_base * config.get_realism_multiplier()
        # health & resources modify growth
        health_factor = (self.health - 50) / 100.0
        resource_factor = 0.0
        if "farmland" in self.resources:
            resource_factor = min(0.05, self.resources["farmland"] / (1e3 + self.population / 1e6))
        growth = base + health_factor * 0.001 + resource_factor
        # logistic cap with stronger convergence
        carrying = config.pop_max * config.pop_carrying_capacity_factor
        logistic_factor = 1 - (self.population / carrying) * config.pop_logistic_strength
        self.population = float(self.population * (1 + growth) * logistic_factor)
        self.population = max(0.0, self.population)

    def update_stability(self, config) -> None:
        """Update political stability slowly with random shocks and economic health."""
        economic_factor = (self.gdp / (1 + self.get_gdp_per_capita())) * 0.0
        shock = random.uniform(-1.0, 1.0)
        self.stability = float(max(0.0, min(100.0, self.stability + shock * 0.5 - economic_factor * 0.0)))

    # helper
    def get_gdp_per_capita(self) -> float:
        return float(self.gdp / max(1.0, self.population))

    def to_dict(self) -> Dict[str, any]:
        """Serialize nation state for data collection."""
        return {
            "id": self.id,
            "name": self.name,
            "population": self.population,
            "gdp": self.gdp,
            "gdp_per_capita": self.get_gdp_per_capita(),
            "technology": self.technology,
            "health": self.health,
            "stability": self.stability,
            "ideology": self.ideology,
            "government_type": self.government_type,
            "military_power": self.military_power.copy(),
            "is_at_war": self.is_at_war,
            "war_exhaustion": self.war_exhaustion,
            "resources": self.resources.copy(),
            "resources_extracted": self.resources_extracted.copy(),
            "currency": {
                "name": self.currency.name,
                "exchange_rate": self.currency.exchange_rate,
                "regime": self.currency.regime,
                "reserves": self.currency.reserves
            },
            "debt_to_gdp": max(0.0, self.debt_to_gdp),
            "inflation_rate": self.inflation_rate,
            "trade_balance": self.trade_balance,
            "fdi_inflows": self.fdi_inflows,
            "fdi_outflows": self.fdi_outflows,
            "alliances": list(self.alliances),
            "sanctions_from": list(self.sanctions_from),
            "colonial_subjects": list(self.colonial_subjects)
        }