import pytest
from pathlib import Path
import tempfile
from reporting import ReportGenerator
from config import SimulationConfig

@pytest.fixture
def config():
    return SimulationConfig(
        num_nations=5,
        num_steps=10,
        realism_level="high",
        enable_gold_standard=False,
        output_dir=Path(".")
    )

def test_generate_report(config):
    """Test HTML report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        generator = ReportGenerator(config)
        
        # Dummy history
        history = [
            {
                "step": 0,
                "events": ["Simulation started"],
                "global_stats": {
                    "living_nations": 5,
                    "global_gdp": 1e12,
                    "global_population": 1e9,
                    "climate_index": 0
                }
            },
            {
                "step": 1,
                "events": ["Something happened"],
                "global_stats": {
                    "living_nations": 5,
                    "global_gdp": 1.1e12,
                    "global_population": 1.01e9,
                    "climate_index": 1
                }
            }
        ]
        
        report_path = generator.generate_report(history, output_dir)
        
        assert report_path.exists()
        content = report_path.read_text()
        
        assert "GeoSim AI Run" in content
        assert "Something happened" in content
        assert "1.10T" in content # GDP formatting check
