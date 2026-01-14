import pytest
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
from pathlib import Path
import shutil
import tempfile
from nation import Nation, Currency
from config import SimulationConfig
from world import World
from viz import Visualizer
from geography import HexGrid, TerrainType

@pytest.fixture
def config():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield SimulationConfig(
            num_nations=5,
            num_steps=10,
            realism_level="high",
            enable_gold_standard=False,
            output_dir=Path(tmpdir)
        )

def test_create_world_map(config):
    """Test map generation with hex grid."""
    viz = Visualizer(config)
    
    # Create dummy data
    hex_grid = HexGrid(20, 20)
    hex_grid.generate_terrain(seed=42)
    
    nations = []
    for i in range(3):
        c = Currency(f"C{i}")
        n = Nation(i, f"N{i}", "Democracy", 1e6, 1e11, 50, {}, 50, 50, 50, c)
        # Assign some territory
        n.territory_tiles = [(i*2, i*2), (i*2+1, i*2)]
        nations.append(n)
        
    # Generate map
    viz.create_world_map(nations, 0, 0.0, hex_grid)
    
    # Check file exists
    output_file = config.output_dir / "world_map_step_0000.png"
    assert output_file.exists()
    assert output_file.stat().st_size > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
