
import pytest
from nation import Nation, Currency
from world import World
from economy import GlobalEconomy
from diplomacy import UnitedNations
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

def test_trade_distance_logic(config):
    """Test that trade volume decreases with distance."""
    economy = GlobalEconomy(config)
    
    # Create 3 nations
    n1 = Nation(0, "N1", "Democracy", 10e6, 1e12, 50, {}, 80, 0, 80, Currency("C1"))
    n2 = Nation(1, "N2", "Democracy", 10e6, 1e12, 50, {}, 80, 0, 80, Currency("C2")) # Close to N1
    n3 = Nation(2, "N3", "Democracy", 10e6, 1e12, 50, {}, 80, 0, 80, Currency("C3")) # Far from N1
    
    # Assign territories
    # N1 at (0,0)
    n1.territory_tiles = [(0,0)]
    # N2 at (1,1) -> Distance ~1.41
    n2.territory_tiles = [(1,1)]
    # N3 at (50,50) -> Distance ~70.7
    n3.territory_tiles = [(50,50)]
    
    nations = [n1, n2, n3]
    
    economy.update_trade_network(nations)
    
    vol_1_2 = economy.trade_volumes.get((0,1), 0)
    vol_1_3 = economy.trade_volumes.get((0,2), 0)
    
    print(f"Trade N1-N2 (Close): {vol_1_2}")
    print(f"Trade N1-N3 (Far): {vol_1_3}")
    
    assert vol_1_2 > vol_1_3 * 10 # Should be significantly higher (distance squared)

def test_colonial_tribute(config):
    """Test that colonial subjects pay tribute."""
    economy = GlobalEconomy(config)
    
    master = Nation(0, "Master", "Autocracy", 10e6, 1e12, 80, {}, 80, 0, 80, Currency("MST"))
    subject = Nation(1, "Subject", "Democracy", 10e6, 1e11, 20, {}, 50, 0, 80, Currency("SBJ"))
    
    master.colonial_subjects.add(subject.id)
    
    initial_master_gdp = master.gdp
    initial_subject_gdp = subject.gdp
    
    economy.process_colonial_relations([master, subject])
    
    # Tribute is 3% of subject GDP
    expected_tribute = initial_subject_gdp * 0.03
    
    assert master.gdp > initial_master_gdp
    assert subject.gdp < initial_subject_gdp
    assert abs((master.gdp - initial_master_gdp) - expected_tribute) < 1e6

def test_un_veto_logic(config):
    """Test that allies veto sanctions."""
    un = UnitedNations(config)
    
    # Create nations
    us = Nation(0, "US", "Democracy", 100e6, 20e12, 90, {}, 90, 0, 90, Currency("USD"))
    ally = Nation(1, "Ally", "Democracy", 10e6, 1e12, 80, {}, 80, 0, 80, Currency("ALY"))
    enemy = Nation(2, "Enemy", "Autocracy", 10e6, 1e12, 50, {}, 50, 0, 50, Currency("ENM"))
    
    nations = [us, ally, enemy]
    
    # US in security council
    un.security_council = {us.id}
    
    # US allied with Ally
    us.alliances.add(ally.id)
    
    # Propose sanctions on Ally (should be vetoed by US)
    # We force random to return < 0.9 for veto check (veto probability is 90% if conditions met)
    
    # Let's try multiple times to be statistically sure
    vetoed_count = 0
    for _ in range(100):
        passed = un.propose_resolution(enemy, "sanctions", ally, nations)
        if not passed:
            vetoed_count += 1
            
    print(f"Vetoed {vetoed_count}/100 times")
    assert vetoed_count > 50 # Should be around 90
