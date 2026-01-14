
import unittest
from nation import Nation, Currency
from economy import GlobalEconomy
from world import World
from config import SimulationConfig

class TestCriticalFixes(unittest.TestCase):
    def setUp(self):
        from pathlib import Path
        self.config = SimulationConfig(
            num_nations=10,
            num_steps=100,
            realism_level="medium",
            enable_gold_standard=False,
            output_dir=Path("test_output")
        )
        self.economy = GlobalEconomy(self.config)

    def test_gdp_calibration(self):
        """Verify GDP is in realistic range for standard inputs."""
        # Standard Nation: 20M pop, Tech 40
        currency = Currency("TEST")
        # Initial GDP must be realistic for capital stock calculation (K=3*GDP)
        # 20M * 15k = 300B
        nation = Nation(
            id=0, name="TestLand", government_type="Democracy",
            population=20e6, gdp=300e9, 
            technology=40, military_power={}, health=50,
            ideology=0, stability=80, currency=currency
        )
        
        # Calculate GDP
        gdp = nation.calculate_gdp(self.config)
        
        # Expected: ~$15k per capita -> $300B
        # Allow range $200B - $500B
        print(f"Calculated GDP: ${gdp/1e9:.2f}B")
        self.assertTrue(200e9 <= gdp <= 500e9, f"GDP ${gdp/1e9:.2f}B out of realistic range (200-500B)")

    def test_capital_flight_accounting(self):
        """Verify capital flight reduces investor assets and target liabilities."""
        # Setup Investor and Target
        # Set Investor GDP low (<1e11) to prevent "New Investment Phase" from interfering
        investor = Nation(0, "Investor", "Democracy", 50e6, 50e9, 80, {}, 80, 0, 90, Currency("INV"))
        target = Nation(1, "Target", "Autocracy", 20e6, 200e9, 30, {}, 40, 0, 20, Currency("TGT")) # Low stability
        
        # Initial Position
        investor.fdi_positions[1] = 10e9 # $10B investment
        investor.fdi_outflows = 100e9 # Previous outflows
        target.fdi_inflows = 50e9 # Previous inflows
        
        # Trigger Flight
        # We need to mock the nations list
        nations = [investor, target]
        
        # Run economy process (which triggers flight due to low stability)
        self.economy.process_fdi_flows(nations)
        
        # Check results
        # Flight severity for stability < 40 is 0.2
        expected_flight = 10e9 * 0.2
        
        # Investor outflow should DECREASE (repatriation)
        self.assertLess(investor.fdi_outflows, 100e9)
        self.assertAlmostEqual(investor.fdi_outflows, 100e9 - expected_flight)
        
        # Target inflow should DECREASE (capital leaving)
        self.assertLess(target.fdi_inflows, 50e9)
        self.assertAlmostEqual(target.fdi_inflows, 50e9 - expected_flight)
        
        print(f"Capital Flight Verified: {expected_flight/1e9}B repatriated.")

    def test_empty_world_safety(self):
        """Verify world methods don't crash with no living nations."""
        world = World(self.config)
        world.nations = [] # Kill everyone
        
        try:
            world.print_summary(0)
            world.generate_final_report()
        except Exception as e:
            self.fail(f"Empty world caused crash: {e}")

if __name__ == '__main__':
    unittest.main()
