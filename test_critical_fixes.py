import pytest
import random
from nation import Nation, Currency
from world import World
from economy import GlobalEconomy
from config import SimulationConfig
from pathlib import Path

@pytest.fixture
def config():
    return SimulationConfig(
        num_nations=5,
        num_steps=10,
        realism_level="high",
        enable_gold_standard=True,
        output_dir=Path("./output")
    )

def test_cobb_douglas_gdp(config):
    """Test that GDP follows Cobb-Douglas properties."""
    currency = Currency("TEST")
    nation = Nation(0, "Testland", "Democracy", 10e6, 1e12, 50, {}, 80, 0, 80, currency)
    
    # Initial GDP check
    initial_gdp = nation.calculate_gdp(config)
    
    # Increase Capital (Investment)
    nation.capital_stock *= 1.1  # +10% Capital
    gdp_high_k = nation.calculate_gdp(config)
    
    # Increase Labor (Population)
    nation.capital_stock /= 1.1 # Reset K
    nation.population *= 1.1 # +10% Labor
    gdp_high_l = nation.calculate_gdp(config)
    
    # Cobb-Douglas property: Returns to scale (if alpha + beta = 1)
    # With alpha=0.33, 10% increase in K should increase GDP by ~3.3%
    # 10% increase in L should increase GDP by ~6.7%
    
    k_impact = gdp_high_k / initial_gdp
    l_impact = gdp_high_l / initial_gdp
    
    print(f"K Impact: {k_impact}, L Impact: {l_impact}")
    
    assert k_impact > 1.0
    assert l_impact > 1.0
    # L impact should be higher than K impact (0.67 vs 0.33)
    assert l_impact > k_impact

def test_hubbert_curve(config):
    """Test that resource extraction follows a bell curve shape."""
    world = World(config)
    nation = world.nations[0]
    nation.resources["oil"] = 1000.0
    nation.resources_initial["oil"] = 1000.0
    nation.resources_extracted["oil"] = 0.0
    
    extractions = []
    
    # Speed up depletion for test
    config.resource_depletion_rate = 0.2
    
    # Simulate depletion
    for _ in range(200):
        prev_extracted = nation.resources_extracted["oil"]
        world._extract_resources()
        curr_extracted = nation.resources_extracted["oil"]
        extractions.append(curr_extracted - prev_extracted)
        
        if nation.resources["oil"] <= 0:
            break
            
    # Check for peak
    peak_extraction = max(extractions)
    peak_index = extractions.index(peak_extraction)
    
    print(f"Peak at step {peak_index} with {peak_extraction}")
    
    # Should start low, rise to peak, then fall
    assert peak_index > 0
    assert peak_index < len(extractions) - 1
    assert extractions[0] < peak_extraction
    assert extractions[-1] < peak_extraction
    
    # Check for asymmetry (Peak should be early, around 40%)
    # With 100 steps, peak should be around 40.
    # Allow some buffer
    assert 30 <= peak_index <= 50

def test_gold_standard_crisis(config):
    """Test that gold standard nations face crisis when reserves deplete."""
    currency = Currency("GOLD", regime="gold")
    currency.gold_reserves = 0.5 # Very low reserves
    
    # Simulate persistent deficit
    bop_deficit = -0.5 # Large deficit -> drain 0.05 per step
    
    # Step 1: Reserves drain
    currency.update_exchange_rate(bop_deficit, 0.0, config)
    assert currency.gold_reserves < 0.5
    
    # Step 2: Drain until empty
    # Should take ~10 steps max
    for _ in range(20):
        currency.update_exchange_rate(bop_deficit, 0.0, config)
        if currency.regime == "floating":
            break
            
    assert currency.regime == "floating"
    assert currency.gold_reserves == 0.0
    # Should have devalued
    assert currency.exchange_rate < 1.0

def test_capital_flight(config):
    """Test that investors flee unstable nations."""
    economy = GlobalEconomy(config)
    
    # Investor is poor so they don't have budget for NEW investment (threshold 1e11)
    # But we manually set a position
    investor = Nation(0, "Rich", "Democracy", 10e6, 5e10, 50, {}, 80, 0, 80, Currency("USD"))
    target = Nation(1, "Poor", "Autocracy", 10e6, 1e11, 20, {}, 50, 0, 80, Currency("PES"))
    
    nations = [investor, target]
    
    # Establish position
    investor.fdi_positions[target.id] = 1e9 # $1B investment
    initial_gdp = target.gdp
    
    # Trigger instability
    target.stability = 20 # Crisis!
    
    economy.process_fdi_flows(nations)
    
    # Check flight
    print(f"Position: {investor.fdi_positions.get(target.id, 0)}")
    assert investor.fdi_positions.get(target.id, 0) < 1e9
    assert target.gdp < initial_gdp # Economic shock
    
    # Check flows (Updated logic: Flight = Negative Inflow for target, Negative Outflow for investor)
    assert target.fdi_inflows < 0
    assert investor.fdi_outflows < 0
