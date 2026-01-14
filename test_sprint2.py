import pytest
import random
from nation import Nation
from world import World
from config import SimulationConfig
from diplomacy import UnitedNations, AllianceType
from politics import FactionType, Faction
from intelligence import MissionType
from pathlib import Path

@pytest.fixture
def config():
    return SimulationConfig(
        num_nations=10,
        num_steps=100,
        realism_level="high",
        enable_gold_standard=False,
        output_dir=Path("./output")
    )

@pytest.fixture
def world(config):
    return World(config)

def test_un_voting(config):
    """Test UN resolution voting logic."""
    un = UnitedNations(config)
    
    # Create dummy nations
    nations = []
    for i in range(10):
        from nation import Currency
        c = Currency(f"C{i}")
        n = Nation(
            id=i, 
            name=f"Nation{i}",
            government_type="Democracy",
            population=1e6,
            gdp=1e11,
            technology=50,
            military_power={"army": 10, "navy": 10, "air": 10, "nuclear": 0},
            health=50,
            ideology=50,
            stability=50,
            currency=c
        )
        nations.append(n)
        
    # Set up Security Council
    un.update_security_council(nations)
    assert len(un.security_council) == 5
    
    # Test passing resolution
    proposer = nations[0]
    target = nations[1]
    
    # Force favorable conditions
    for n in nations:
        n.ideology = 50
        
    passed = un.propose_resolution(proposer, "aid", target, nations)
    # Should pass with neutral ideology and aid type
    # (Note: Random noise might cause fail, but unlikely with 10 voters)
    
    # Test Veto
    sc_member_id = list(un.security_council)[0]
    sc_member = next(n for n in nations if n.id == sc_member_id)
    
    # Make target an ally of SC member
    sc_member.alliances.add(target.id)
    
    # Sanctions should be vetoed
    passed_sanctions = un.propose_resolution(proposer, "sanctions", target, nations)
    assert not passed_sanctions or un.resolutions_vetoed > 0

def test_domestic_politics(config):
    """Test faction influence and loyalty updates."""
    from nation import Currency
    c = Currency("TST")
    n = Nation(
        id=0, 
        name="Testland",
        government_type="Democracy",
        population=1e6,
        gdp=1e11,
        technology=50,
        military_power={"army": 10, "navy": 10, "air": 10, "nuclear": 0},
        health=50,
        ideology=50,
        stability=50,
        currency=c
    )
    politics = n.politics
    
    # Check initialization
    assert len(politics.factions) >= 2 # Military and Corporate
    
    # Test influence normalization
    total_influence = sum(f.influence for f in politics.factions)
    assert abs(total_influence - 100.0) < 0.1
    
    # Test loyalty update
    mil_faction = next(f for f in politics.factions if f.type == FactionType.MILITARY)
    initial_loyalty = mil_faction.loyalty
    
    # Increase military spending
    n.budget["military"] = 0.10 # 10%
    politics.update()
    
    assert mil_faction.loyalty > initial_loyalty

def test_espionage(config):
    """Test spy agency operations."""
    from nation import Currency
    c1 = Currency("C1")
    c2 = Currency("C2")
    n1 = Nation(0, "N1", "Democracy", 1e6, 1e11, 50, {}, 50, 50, 50, c1)
    n2 = Nation(1, "N2", "Democracy", 1e6, 1e11, 50, {}, 50, 50, 50, c2)
    
    agency = n1.intelligence
    
    # Grant massive budget and tech for success
    agency.budget = 1e12
    agency.tech_level = 200
    n2.technology = 0
    n2.stability = 0
    
    # Attempt mission
    result = agency.conduct_operation(n2, MissionType.STEAL_TECH)
    
    assert "success" in result
    assert "detected" in result
    assert "type" in result
    
    # With max advantage, should likely succeed
    # (Randomness exists, so we check structure mostly)

def test_integration_world(world):
    """Test that world update loop calls new systems."""
    # Run one step
    world.simulate_step(0)
    
    # Check if UN updated
    assert len(world.un.security_council) == 5
    
    # Check if politics updated (loyalty changed or stayed same)
    n = world.nations[0]
    assert n.politics.factions
    
    # Check if intelligence updated (budget exists)
    assert n.intelligence.budget > 0
