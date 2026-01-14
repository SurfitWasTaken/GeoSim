from world import World
from config import SimulationConfig
from pathlib import Path

config = SimulationConfig(
    num_nations=10,
    num_steps=100,
    realism_level="high",
    enable_gold_standard=False,
    output_dir=Path("test_output")
)
world = World(config)
world.cumulative_carbon = 2.0e12
print("Calling _update_climate...")
world._update_climate()
print(f"Tipping points: {world.tipping_points_triggered}")
