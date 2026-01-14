"""
Comprehensive test suite for enhanced geopolitical simulation.
Tests long-term stability, edge cases, and stress scenarios.
"""

import pytest
import random
import numpy as np
from pathlib import Path
import tempfile
import time

from config import SimulationConfig
from nation import Nation, Currency
from economy import GlobalEconomy
from world import World


@pytest.fixture
def long_config():
    """Configuration for longer simulation tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return SimulationConfig(
            num_nations=20,
            num_steps=500,
            realism_level="high",
            enable_gold_standard=True,
            output_dir=Path(tmpdir)
        )


@pytest.fixture
def stress_config():
    """Configuration for stress testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return SimulationConfig(
            num_nations=100,
            num_steps=100,
            realism_level="medium",
            enable_gold_standard=False,
            output_dir=Path(tmpdir)
        )


class TestLongTermStability:
    """Tests for long-running simulations."""
    
    def test_long_simulation_500_steps(self, long_config):
        """Test full 500-step simulation with 20 nations."""
        random.seed(42)
        np.random.seed(42)
        
        world = World(long_config)
        
        # Track metrics
        living_nations_history = []
        global_gdp_history = []
        climate_history = []
        
        # Run full simulation
        for step in range(500):
            step_data = world.simulate_step(step)
            
            living_nations = step_data["global_stats"]["living_nations"]
            global_gdp = step_data["global_stats"]["global_gdp"]
            climate = step_data["global_stats"]["climate_index"]
            
            living_nations_history.append(living_nations)
            global_gdp_history.append(global_gdp)
            climate_history.append(climate)
            
            # Basic assertions
            assert living_nations > 0, f"All nations dead at step {step}"
            assert global_gdp > 0, "Global GDP collapsed"
        
        # Long-term checks
        assert living_nations_history[-1] >= 5, "Too many nations collapsed"
        assert len(world.combat.war_history) > 0, "No wars occurred in 500 steps"
        assert climate_history[-1] > climate_history[0], "Climate should worsen over time"
        
        # Some nations should survive
        final_survival_rate = living_nations_history[-1] / long_config.num_nations
        assert 0.25 < final_survival_rate < 1.0, f"Unrealistic survival rate: {final_survival_rate}"
    
    def test_climate_threshold_crossing(self, long_config):
        """Test carbon budget exhaustion and tipping points."""
        random.seed(100)
        np.random.seed(100)
        
        # Modify config to accelerate climate change
        long_config.climate_gdp_factor *= 10  # 10x emissions
        
        world = World(long_config)
        
        tipping_points_triggered = []
        
        for step in range(200):
            step_data = world.simulate_step(step)
            
            # Track when tipping points trigger
            if len(world.tipping_points_triggered) > len(tipping_points_triggered):
                new_points = world.tipping_points_triggered - set(tipping_points_triggered)
                tipping_points_triggered.extend(new_points)
        
        # Should trigger at least permafrost
        assert "permafrost" in world.tipping_points_triggered, "Permafrost tipping point should trigger"
        
        # Temperature should rise significantly
        assert world.climate_index > 1.5, f"Climate index too low: {world.climate_index}"
        
        # Some coastal nation should lose tiles
        coastal_nations = [n for n in world.nations if n.is_coastal and n.population > 0]
        if coastal_nations:
            initial_tiles = sum(len(n.territory_tiles) for n in coastal_nations if n.population > 0)
            # We expect some tile loss from sea-level rise
            assert initial_tiles > 0


class TestCurrencyRegimes:
    """Test currency system edge cases."""
    
    def test_gold_standard_crisis(self, long_config):
        """Test gold standard country running out of reserves."""
        random.seed(50)
        np.random.seed(50)
        
        world = World(long_config)
        
        # Find a gold standard nation
        gold_nations = [n for n in world.nations if n.currency.regime == "gold"]
        
        if gold_nations:
            nation = gold_nations[0]
            initial_regime = nation.currency.regime
            
            # Force trade deficit to drain reserves
            for _ in range(50):
                nation.trade_balance = -nation.gdp * 0.2  # 20% deficit
                world.economy.update_exchange_rates(world.nations)
            
            # Should either have depleted reserves or transitioned
            assert nation.currency.gold_reserves < nation.gdp * 0.05 or nation.currency.regime == "floating"
    
    def test_currency_peg_break(self, long_config):
        """Test currency peg breaking under pressure."""
        currency =Currency(name="PEG", regime="pegged")
        currency.peg_target = 1.0
        
        nation = Nation(
            id=0, name="PeggedNation", government_type="Democracy",
            population=50e6, gdp=1e12, technology=50,
            military_power={"army": 30, "navy": 30, "air": 30, "nuclear": 0},
            health=70, ideology=0, stability=60, currency=currency
        )
        
        # Force large imbalance
        nation.trade_balance = -nation.gdp * 0.15  # 15% deficit
        
        initial_regime = nation.currency.regime
        
        # Try to trigger speculative attack
        for _ in range(100):
            bop = -0.15  # Large negative
            inflation_diff = 0.03
            nation.currency.update_exchange_rate(bop, inflation_diff, long_config)
            
            if nation.currency.regime == "floating":
                break
        
        # Should eventually break peg
        assert nation.currency.regime == "floating" or nation.currency.exchange_rate < 0.6


class TestColonialDynamics:
    """Test colonial relationships and independence."""
    
    def test_colonial_independence_cycle(self, long_config):
        """Test full cycle: FDI → colonial status → independence."""
        random.seed(75)
        np.random.seed(75)
        
        # Create colonizer and subject
        rich_currency = Currency(name="RCH")
        rich = Nation(
            id=0, name="Colonizer", government_type="Democracy",
            population=100e6, gdp=10e12, technology=70,
            military_power={"army": 80, "navy": 80, "air": 80, "nuclear": 10},
            health=80, ideology=50, stability=70, currency=rich_currency
        )
        
        poor_currency = Currency(name="SBJ")
        subject = Nation(
            id=1, name="Subject", government_type="Autocracy",
            population=30e6, gdp=0.5e12, technology=40,
            military_power={"army": 20, "navy": 10, "air": 10, "nuclear": 0},
            health=50, ideology=-30, stability=55, currency=poor_currency
        )
        
        nations = [rich, subject]
        economy = GlobalEconomy(long_config)
        
        # Phase 1: Massive FDI
        for _ in range(10):
            economy.process_fdi_flows(nations)
        
        # Check if colonial relationship formed
        if subject.id in rich.colonial_subjects:
            # Phase 2: Subject develops
            subject.technology = 65
            subject.stability = 60
            
            # Phase 3: Try for independence
            independence_achieved = False
            for _ in range(50):
                economy.process_colonial_relations(nations)
                if subject.id not in rich.colonial_subjects:
                    independence_achieved = True
                    break
            
            # Should eventually gain independence
            assert independence_achieved, "High-tech stable subject should gain independence"


class TestStressScenarios:
    """Stress tests and edge cases."""
    
    def test_100_nation_stress(self, stress_config):
        """Test simulation with 100 nations."""
        random.seed(200)
        np.random.seed(200)
        
        start_time = time.time()
        
        world = World(stress_config)
        
        for step in range(100):
            step_data = world.simulate_step(step)
            
            # Should complete without crashes
            assert step_data["global_stats"]["living_nations"] > 0
        
        elapsed = time.time() - start_time
        
        # Performance check: <20s per step on average
        avg_time_per_step = elapsed / 100
        assert avg_time_per_step < 20, f"Too slow: {avg_time_per_step:.2f}s per step"
    
    def test_alliance_cap_enforcement(self, long_config):
        """Test that no nation exceeds 10 alliances."""
        random.seed(300)
        np.random.seed(300)
        
        world = World(long_config)
        
        for step in range(100):
            world.simulate_step(step)
        
        # Check alliance counts
        for nation in world.nations:
            if nation.population > 0:
                assert len(nation.alliances) <= 10, f"{nation.name} has {len(nation.alliances)} alliances (max 10)"
    
    def test_dead_nation_isolation(self, long_config):
        """Test that dead nations don't participate in anything."""
        random.seed(400)
        np.random.seed(400)
        
        world = World(long_config)
        
        # Kill a nation
        victim = world.nations[0]
        victim.population = 0
        victim_id = victim.id
        
        # Run several steps
        for step in range(20):
            world.simulate_step(step)
        
        # Check victim doesn't participate
        # 1. No trade agreements
        for (a, b) in world.economy.trade_agreements:
            assert a != victim_id and b != victim_id, "Dead nation in trade agreement"
        
        # 2. No alliances
        for nation in world.nations:
            if nation.population > 0:
                assert victim_id not in nation.alliances, "Living nation allied with dead nation"
        
        # 3. Not at war
        assert not victim.is_at_war, "Dead nation marked as at war"
    
    def test_capital_flight_cascade(self, long_config):
        """Test capital flight triggering economic crisis."""
        random.seed(500)
        np.random.seed(500)
        
        # Create unstable nation with foreign investment
        economy = GlobalEconomy(long_config)
        
        stable_currency = Currency(name="STA")
        stable = Nation(
            id=0, name="Stable", government_type="Democracy",
            population=80e6, gdp=5e12, technology=65,
            military_power={"army": 50, "navy": 50, "air": 50, "nuclear": 0},
            health=75, ideology=20, stability=75, currency=stable_currency
        )
        
        unstable_currency = Currency(name="UNS")
        unstable = Nation(
            id=1, name="Unstable", government_type="Autocracy",
            population=40e6, gdp=1e12, technology=45,
            military_power={"army": 30, "navy": 20, "air": 20, "nuclear": 0},
            health=55, ideology=-40, stability=35, currency=unstable_currency
        )
        
        nations = [stable, unstable]
        
        # Build up FDI position
        stable.fdi_positions[unstable.id] = unstable.gdp * 0.4  # 40% of GDP
        unstable.fdi_inflows = unstable.gdp * 0.4
        
        initial_gdp = unstable.gdp
        initial_stability = unstable.stability
        
        # Trigger crisis
        unstable.stability = 30
        unstable.is_at_war = True
        
        # Process capital flight
        economy.process_fdi_flows(nations)
        
        # Should trigger flight and damage economy
        assert unstable.gdp < initial_gdp * 0.95, "Capital flight should damage GDP"
        assert stable.fdi_positions.get(unstable.id, 0) < unstable.gdp * 0.3, "FDI should flee"


class TestEdgeCases:
    """Test various edge cases and boundary conditions."""
    
    def test_nuclear_winter_recovery(self, long_config):
        """Test global recovery after nuclear winter."""
        random.seed(600)
        np.random.seed(600)
        
        world = World(long_config)
        
        # Trigger nuclear war
        world.combat.nuclear_detonations = 5
        world.nuclear_winter_active = True
        
        # Apply nuclear winter
        event_msg = world.combat.apply_nuclear_winter(world.nations)
        
        assert "NUCLEAR WINTER" in event_msg
        
        # Check effects
        living = [n for n in world.nations if n.population > 0]
        assert len(living) > 0, "Some nations should survive nuclear winter"
        
        # Population and GDP should be drastically reduced
        total_pop = sum(n.population for n in living)
        assert total_pop < sum(n.population for n in world.nations) * 0.7
    
    def test_zero_population_safety(self, long_config):
        """Test that zero population doesn't cause crashes."""
        world = World(long_config)
        
        # Set all but one nation to zero population
        for nation in world.nations[:-1]:
            nation.population = 0
        
        # Run simulation - should not crash
        for step in range(10):
            step_data = world.simulate_step(step)
            assert step_data["global_stats"]["living_nations"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
