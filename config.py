"""
Configuration and constants for realistic geopolitical simulation.
Parameters calibrated to empirical data and established economic models.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class SimulationConfig:
    """Global simulation configuration with realistic parameters."""
    
    num_nations: int
    num_steps: int
    realism_level: Literal["low", "medium", "high"]
    enable_gold_standard: bool
    output_dir: Path
    
    # World geography (hex-grid on torus)
    world_width: int = 100
    world_height: int = 100
    
    # Population parameters (UN data calibration)
    pop_min: float = 1e6  # 1 million
    pop_max: float = 200e6  # 200 million
    pop_growth_base: float = 0.012  # ~1.2% annual (world average)
    pop_growth_std: float = 0.008
    pop_carrying_capacity_factor: float = 1.5
    pop_logistic_strength: float = 0.0001  # Stronger convergence to carrying capacity
    
    # GDP parameters (Solow-Swan inspired)
    gdp_min: float = 0.1e12  # $0.1 trillion
    gdp_max: float = 20e12  # $20 trillion
    capital_share_alpha: float = 0.33  # Cobb-Douglas parameter
    tfp_growth_base: float = 0.015  # Total factor productivity growth
    depreciation_rate: float = 0.05  # Capital depreciation
    
    # Technology (0-100 scale)
    tech_min: int = 10
    tech_max: int = 60
    tech_rd_efficiency: float = 0.15  # R&D spending to tech conversion
    tech_spillover_rate: float = 0.05  # Knowledge diffusion from trade
    tech_nuclear_threshold: int = 80
    tech_space_threshold: int = 90
    
    # Military parameters (Stockholm Peace Research Institute data)
    military_gdp_cost: float = 0.02  # 2% of GDP per unit of military power
    military_buildup_rate: float = 5.0  # Max annual increase
    military_decay_rate: float = 0.03  # Depreciation without maintenance
    
    # Health system (WHO indices)
    health_min: int = 30
    health_max: int = 85
    health_gdp_elasticity: float = 0.15
    health_tech_bonus: float = 0.2
    
    # Currency and monetary policy
    base_inflation_target: float = 0.02  # 2% target (Fed/ECB standard)
    exchange_rate_volatility: float = 0.08  # Annual forex volatility
    interest_rate_response: float = 1.5  # Taylor rule coefficient
    
    # Trade and globalization (WTO/IMF data)
    trade_comparative_advantage_boost: float = 0.03  # 3% GDP boost
    trade_route_distance_penalty: float = 0.001  # Per-tile distance cost
    fdi_return_rate: float = 0.06  # Expected FDI returns
    fdi_risk_premium: float = 0.04  # Risk-adjusted spread
    
    # Resource extraction (Hubbert curve)
    resource_depletion_rate: float = 0.02  # 2% annual extraction
    resource_efficiency_tech_factor: float = 0.01  # Tech reduces extraction
    
    # Climate change (IPCC RCP scenarios)
    climate_gdp_factor: float = 2e-15  # CO2 per GDP
    climate_resource_factor: float = 0.5  # Extraction emissions multiplier
    climate_migration_threshold: int = 60  # Climate refugees trigger
    carbon_budget_2c: float = 3.7e12  # Cumulative CO2 budget for <2°C (tons)
    climate_temp_scaling: float = 1.5  # Climate index to temperature conversion
    
    # Conflict probabilities (Uppsala Conflict Data Program)
    war_base_probability: float = 0.02
    war_ideology_factor: float = 0.001
    war_resource_factor: float = 0.015
    rebellion_instability_threshold: float = 30
    
    # Institutions
    un_veto_gdp_threshold: int = 5  # Top-5 GDP nations get veto
    central_bank_inflation_tolerance: float = 0.01  # 1% deviation tolerance
    
    # Events (empirical frequency calibration)
    event_election_prob: float = 0.25  # Democracies, per year
    event_coup_base_prob: float = 0.01
    event_disaster_prob: float = 0.03
    event_pandemic_prob: float = 0.005  # ~1 per 200 years
    
    # Pandemic parameters (COVID-19 calibrated)
    pandemic_r0_mean: float = 2.5
    pandemic_r0_std: float = 1.0
    pandemic_lethality_mean: float = 0.01
    pandemic_lethality_std: float = 0.005
    pandemic_vaccine_time_mean: int = 15  # months
    
    def get_realism_multiplier(self) -> float:
        """Return parameter strictness multiplier based on realism level."""
        return {"low": 0.5, "medium": 0.75, "high": 1.0}[self.realism_level]


# Government types with stability modifiers (Polity V data)
GOVERNMENT_TYPES = {
    "Democracy": {"stability_base": 65, "growth_bonus": 0.01, "war_reluctance": 0.7},
    "Autocracy": {"stability_base": 50, "growth_bonus": 0.005, "war_reluctance": 0.4},
    "Theocracy": {"stability_base": 55, "growth_bonus": 0.003, "war_reluctance": 0.5},
    "Technocracy": {"stability_base": 70, "growth_bonus": 0.015, "war_reluctance": 0.6},
    "Anarchy": {"stability_base": 20, "growth_bonus": -0.01, "war_reluctance": 0.2}
}

# Realistic nation name generation pool
NATION_NAME_PARTS = {
    "prefixes": ["North", "South", "East", "West", "New", "Greater", "United"],
    "roots": ["Aria", "Boren", "Calid", "Drakos", "Elaria", "Fendor", "Garvon",
              "Halcyon", "Ithara", "Jorvik", "Kalmar", "Lumeria", "Mordian",
              "Navaria", "Ostara", "Pyrrhia", "Quelmar", "Rhovana", "Solvaria",
              "Tarsus", "Urland", "Vesperia", "Westmark", "Xandria", "Yvoria", "Zephyria"],
    "suffixes": ["ia", "land", "stan", "mark", "burg", "haven", "realm"]
}