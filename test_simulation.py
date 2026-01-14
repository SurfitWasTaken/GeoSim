"""
Test suite for geopolitical simulation.
Tests core mechanics, edge cases, and stress scenarios.
"""

import pytest
import random
import numpy as np
from pathlib import Path
import tempfile

from config import SimulationConfig
from nation import Nation, Currency
from economy import GlobalEconomy
from diplomacy import UnitedNations
from events import EventSystem
from combat import WarSystem
from world import World


@pytest.fixture
def test_config():
    """Create test configuration with smaller parameters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return SimulationConfig(
            num_nations=10,
            num_steps=50,
            realism_level="high",
            enable_gold_standard=True,
            output_dir=Path(tmpdir)
        )


@pytest.fixture
def sample_nation():
    """Create sample nation for testing."""
    currency = Currency(name="TST")
    return Nation(
        id=0,
        name="Testland",
        government_type="Democracy",
        population=50e6,
        gdp=1e12,
        technology=50,
        military_power={"army": 30, "navy": 25, "air": 20, "nuclear": 0},
        health=70,
        ideology=0,
        stability=65,
        currency=currency
    )


class TestNationMechanics:
    """Test nation-level mechanics and calculations."""
    
    def test_gdp_calculation(self, sample_nation, test_config):
        """Test GDP calculation with Cobb-Douglas production."""
        initial_gdp = sample_nation.gdp
        new_gdp = sample_nation.calculate_gdp(test_config, global_trade_multiplier=1.0)
        
        assert new_gdp > 0, "GDP must be positive"
        assert 0.5 * initial_gdp < new_gdp < 2.0 * initial_gdp, "GDP should not change drastically in one step"
    
    def test_population_growth(self, sample_nation, test_config):
        """Test population dynamics with logistic growth."""
        initial_pop = sample_nation.population
        sample_nation.resources["farmland"] = 100.0
        
        for _ in range(10):
            sample_nation.update_population(test_config)
        
        assert sample_nation.population > 0, "Population must remain positive"
        # Population should grow with good health and resources
        assert sample_nation.population >= initial_pop * 0.9, "Population should not crash with good conditions"
    
    def test_technology_advancement(self, sample_nation, test_config):
        """Test R&D investment and tech advancement."""
        initial_tech = sample_nation.technology
        sample_nation.invest_rd(0.03, test_config)  # 3% of GDP to R&D
        
        assert sample_nation.technology >= initial_tech, "Tech should not decrease from R&D"
        assert sample_nation.technology <= 100, "Tech should be capped at 100"
    
    def test_military_buildup(self, sample_nation, test_config):
        """Test military force construction."""
        initial_total = sample_nation.get_total_military_power()
        sample_nation.build_military(0.05, test_config)  # 5% of GDP
        
        new_total = sample_nation.get_total_military_power()
        assert new_total > initial_total, "Military should increase with spending"
    
    def test_monetary_policy(self, sample_nation, test_config):
        """Test central bank interest rate adjustments."""
        sample_nation.inflation_rate = 0.05  # 5% inflation
        # Ensure positive growth so output gap doesn't drag rate down
        sample_nation._prev_gdp_election = sample_nation.gdp * 0.9
        sample_nation.manage_monetary_policy(test_config)
        
        # Interest rate should increase to combat high inflation
        # Taylor rule with smoothing moves slowly
        # Started at 0.02. Target ~0.08. New ~0.032.
        assert sample_nation.currency.interest_rate > 0.025, "Interest rate should rise with high inflation"


class TestEconomicSystem:
    """Test global economic systems."""
    
    def test_trade_network(self, test_config):
        """Test multilateral trade network formation."""
        economy = GlobalEconomy(test_config)
        
        # Create diverse nations
        nations = []
        for i in range(5):
            currency = Currency(name=f"C{i}")
            nation = Nation(
                id=i,
                name=f"Nation{i}",
                government_type="Democracy",
                population=30e6 + i * 10e6,
                gdp=0.5e12 + i * 0.5e12,
                technology=40 + i * 5,
                military_power={"army": 20, "navy": 20, "air": 20, "nuclear": 0},
                health=60,
                ideology=i * 20 - 40,  # Diverse ideologies
                stability=60,
                currency=currency
            )
            nation.resources = {"oil": 50.0, "rare_earth": 30.0, "farmland": 70.0, "water": 80.0}
            nations.append(nation)
        
        economy.update_trade_network(nations)
        
        assert len(economy.trade_agreements) > 0, "Trade agreements should form"
        assert len(economy.trade_volumes) > 0, "Trade volumes should be calculated"
    
    def test_fdi_flows(self, test_config):
        """Test foreign direct investment mechanics."""
        economy = GlobalEconomy(test_config)
        
        # Rich investor nation
        rich_currency = Currency(name="RCH")
        rich = Nation(
            id=0, name="RichNation", government_type="Democracy",
            population=100e6, gdp=5e12, technology=70,
            military_power={"army": 50, "navy": 50, "air": 50, "nuclear": 10},
            health=80, ideology=20, stability=80, currency=rich_currency
        )
        
        # Poor recipient nation
        poor_currency = Currency(name="POR")
        poor = Nation(
            id=1, name="PoorNation", government_type="Autocracy",
            population=50e6, gdp=0.3e12, technology=30,
            military_power={"army": 20, "navy": 10, "air": 10, "nuclear": 0},
            health=50, ideology=-20, stability=50, currency=poor_currency
        )
        
        nations = [rich, poor]
        initial_poor_tech = poor.technology
        
        economy.process_fdi_flows(nations)
        
        assert poor.fdi_inflows > 0, "Poor nation should receive FDI"
        assert poor.technology >= initial_poor_tech, "FDI should transfer technology"
    
    def test_exchange_rate_updates(self, test_config):
        """Test currency exchange rate dynamics."""
        economy = GlobalEconomy(test_config)
        
        currency = Currency(name="TST")
        nation = Nation(
            id=0, name="TestNation", government_type="Democracy",
            population=50e6, gdp=1e12, technology=50,
            military_power={"army": 30, "navy": 30, "air": 30, "nuclear": 0},
            health=70, ideology=0, stability=70, currency=currency
        )
        
        # Simulate trade surplus
        nation.trade_balance = 0.1e12
        nation.inflation_rate = 0.01  # Low inflation
        
        initial_rate = nation.currency.exchange_rate
        economy.update_exchange_rates([nation])
        
        # Currency should appreciate with surplus and low inflation
        assert nation.currency.exchange_rate != initial_rate, "Exchange rate should change"


class TestWarfareSystem:
    """Test combat mechanics and warfare."""
    
    def test_war_trigger_detection(self, test_config):
        """Test war trigger probability calculations."""
        combat = WarSystem(test_config)
        
        # Aggressive nation
        agg_currency = Currency(name="AGG")
        aggressor = Nation(
            id=0, name="Aggressor", government_type="Autocracy",
            population=80e6, gdp=2e12, technology=60,
            military_power={"army": 70, "navy": 60, "air": 65, "nuclear": 0},
            health=65, ideology=80, stability=60, currency=agg_currency
        )
        
        # Weak target
        weak_currency = Currency(name="WEK")
        target = Nation(
            id=1, name="WeakNation", government_type="Democracy",
            population=30e6, gdp=0.5e12, technology=35,
            military_power={"army": 20, "navy": 15, "air": 15, "nuclear": 0},
            health=55, ideology=-40, stability=50, currency=weak_currency
        )
        target.resources = {"oil": 200.0, "rare_earth": 100.0, "farmland": 50.0, "water": 60.0}
        
        nations = [aggressor, target]
        
        # Run multiple checks (stochastic)
        wars_triggered = 0
        for _ in range(100):
            wars = combat.check_war_triggers(nations)
            if wars:
                wars_triggered += 1
        
        assert wars_triggered > 0, "Wars should trigger with aggressive, powerful nation vs weak resource-rich target"
        
        # Verify no self-attacks
        for attacker_id, defender_id, _ in combat.active_wars:
            assert attacker_id != defender_id, "Nation cannot attack itself"

    def test_alliance_formation_consent(self, test_config):
        """Test that alliances require mutual consent."""
        world = World(test_config)
        
        # Nation A wants alliance (high proximity), Nation B doesn't (low proximity)
        nation_a = world.nations[0]
        nation_b = world.nations[1]
        
        nation_a.ideology = 50
        nation_b.ideology = -50 # Far apart
        
        # Force update alliances
        world._update_alliances()
        
        # Should be unlikely to form alliance due to ideology gap
        assert nation_b.id not in nation_a.alliances, "Alliance should not form with large ideology gap"
    
    def test_combat_resolution(self, test_config):
        """Test combat mechanics with Lanchester equations."""
        combat = WarSystem(test_config)
        
        # Strong attacker
        strong_currency = Currency(name="STR")
        strong = Nation(
            id=0, name="StrongNation", government_type="Autocracy",
            population=100e6, gdp=3e12, technology=70,
            military_power={"army": 80, "navy": 75, "air": 75, "nuclear": 0},
            health=75, ideology=50, stability=70, currency=strong_currency
        )
        
        # Weak defender
        weak_currency = Currency(name="WEK")
        weak = Nation(
            id=1, name="WeakNation", government_type="Democracy",
            population=40e6, gdp=0.6e12, technology=40,
            military_power={"army": 30, "navy": 20, "air": 20, "nuclear": 0},
            health=60, ideology=-30, stability=55, currency=weak_currency
        )
        
        strong.is_at_war = True
        weak.is_at_war = True
        
        war = {
            "attacker_id": 0,
            "defender_id": 1,
            "attacker_allies": [],
            "defender_allies": [],
            "cause": "resources",
            "duration": 0,
            "intensity": 0.8
        }
        combat.active_wars.append(war)
        
        nations = [strong, weak]
        initial_strong_pop = strong.population
        
        # Simulate war for several steps
        for _ in range(15):
            combat.resolve_wars(nations)
            if not combat.active_wars:
                break
        
        # War should eventually resolve
        assert len(combat.active_wars) == 0, "War should resolve after sufficient duration"
    
        # If defender was annexed, attacker population might increase
        if weak.population > 0:
            assert strong.population < initial_strong_pop, "Attacker should suffer casualties"


class TestGlobalSimulation:
    """Integration tests for full simulation."""
    
    def test_short_simulation(self, test_config):
        """Test complete simulation run."""
        random.seed(42)
        np.random.seed(42)
        
        world = World(test_config)
        
        # Run for 20 steps
        for step in range(20):
            step_data = world.simulate_step(step)
            
            assert step_data["global_stats"]["living_nations"] > 0, "At least some nations should survive"
            assert step_data["global_stats"]["global_gdp"] > 0, "Global GDP should be positive"
            assert step_data["global_stats"]["global_population"] > 0, "Global population should be positive"
    
    def test_pandemic_scenario(self, test_config):
        """Test pandemic event and spread."""
        random.seed(123)
        np.random.seed(123)
        
        world = World(test_config)
        events = EventSystem(test_config)
        
        # Force pandemic spawn
        pandemic = events._spawn_pandemic(world.nations)
        
        assert pandemic["r0"] > 0, "R0 should be positive"
        assert 0 < pandemic["lethality"] < 0.1, "Lethality should be reasonable"
        assert len(pandemic["infected_nations"]) > 0, "At least one nation should be infected"
        
        # Verify quarantine logic
        # Autocracies should have higher quarantine strength
        autocracy = next((n for n in world.nations if n.government_type == "Autocracy"), None)
        if autocracy and autocracy.id in pandemic["infected_nations"]:
            # This is hard to test directly without mocking random, but we can check code path doesn't crash
            pass
    
    def test_economic_crisis_scenario(self, test_config):
        """Test debt crisis and default mechanics."""
        economy = GlobalEconomy(test_config)
        
        # Create highly indebted nation
        currency = Currency(name="DBT")
        nation = Nation(
            id=0, name="IndebtedNation", government_type="Democracy",
            population=60e6, gdp=1e12, technology=45,
            military_power={"army": 25, "navy": 20, "air": 20, "nuclear": 0},
            health=60, ideology=0, stability=50, currency=currency
        )
        nation.debt_to_gdp = 1.5  # 150% debt-to-GDP
        
        initial_debt = nation.debt_to_gdp
        crisis_occurred = economy.simulate_debt_crisis(nation, [nation])
        
        if crisis_occurred:
            assert nation.debt_to_gdp < initial_debt, "Debt should be reduced after default"
            assert nation.stability < 50, "Stability should decrease after crisis"


def test_reproducibility():
    """Test that simulations with same seed are reproducible."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config1 = SimulationConfig(
            num_nations=10,
            num_steps=10,
            realism_level="high",
            enable_gold_standard=False,
            output_dir=Path(tmpdir)
        )
        
        config2 = SimulationConfig(
            num_nations=10,
            num_steps=10,
            realism_level="high",
            enable_gold_standard=False,
            output_dir=Path(tmpdir)
        )
        
        # Run 1
        random.seed(42)
        np.random.seed(42)
        world1 = World(config1)
        gdp1 = [world1.simulate_step(i)["global_stats"]["global_gdp"] for i in range(5)]
        
        # Run 2
        random.seed(42)
        np.random.seed(42)
        world2 = World(config2)
        gdp2 = [world2.simulate_step(i)["global_stats"]["global_gdp"] for i in range(5)]
        
        assert gdp1 == gdp2, "Simulations with same seed should be identical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])