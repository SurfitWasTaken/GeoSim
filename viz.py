"""
Visualization module for creating world maps and charts.
Generates matplotlib-based visual representations of simulation state.
"""

from typing import List, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection
import numpy as np
from pathlib import Path

from nation import Nation
from config import SimulationConfig
from geography import HexGrid, TerrainType


class Visualizer:
    """Handles all visualization and plotting."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.color_map = {}
        self._generate_colors()
        
        # Terrain colors
        self.terrain_colors = {
            TerrainType.OCEAN: '#1f77b4',    # Blue
            TerrainType.PLAINS: '#2ca02c',   # Green
            TerrainType.FOREST: '#006400',   # Dark Green
            TerrainType.DESERT: '#e377c2',   # Pinkish/Sand (using standard mpl color for now)
            TerrainType.MOUNTAIN: '#7f7f7f'  # Gray
        }
        # Better sand color
        self.terrain_colors[TerrainType.DESERT] = '#F4A460' 
    
    def _generate_colors(self):
        """Generate distinct colors for each nation."""
        np.random.seed(42)  # Consistent colors
        for i in range(self.config.num_nations):
            self.color_map[i] = np.random.rand(3,)
    
    def create_world_map(self, nations: List[Nation], step: int, climate_index: float, hex_grid: HexGrid):
        """
        Create comprehensive world map showing multiple layers of information.
        """
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        fig.suptitle(f'World State - Step {step}', fontsize=16, fontweight='bold')
        
        # 1. Terrain & Territory Map (The main map)
        self._plot_hex_map(axes[0, 0], nations, hex_grid, mode="territory")
        
        # 2. Military Power Map
        self._plot_hex_map(axes[0, 1], nations, hex_grid, mode="military")
        
        # 3. Health/Stability Map
        self._plot_hex_map(axes[1, 0], nations, hex_grid, mode="health")
        
        # 4. Economic Stats
        self._plot_economic_stats(axes[1, 1], nations, climate_index)
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.config.output_dir / f"world_map_step_{step:04d}.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
    
    def _plot_hex_map(self, ax, nations: List[Nation], hex_grid: HexGrid, mode: str = "territory"):
        """
        Plot the world using hexagonal patches.
        mode: 'territory', 'military', 'health'
        """
        patches = []
        colors = []
        
        # Pre-compute nation data for fast lookup
        nation_map = {} # (x,y) -> nation_id
        for nation in nations:
            if nation.population > 0:
                for x, y in nation.territory_tiles:
                    nation_map[(x, y)] = nation
        
        # Hex parameters
        # Odd-q vertical layout
        # x, y are grid coordinates
        # We need to convert to pixel coordinates for plotting
        # h = height of hex, w = width
        # vertical spacing = 3/4 * h
        # horizontal spacing = w
        # w = sqrt(3) * size
        # h = 2 * size
        size = 1.0
        w = np.sqrt(3) * size
        h = 2 * size
        
        for y in range(hex_grid.height):
            for x in range(hex_grid.width):
                # Calculate pixel coordinates (Odd-q)
                px = x * w * 0.75
                py = y * h
                if x % 2 == 1:
                    py += h / 2
                
                # Invert Y for plotting (0 at bottom) or keep as is?
                # Matrix coords usually 0 at top. matplotlib 0 at bottom.
                # Let's flip py to match matrix orientation visually
                py = -py
                
                # Create hex patch
                hex_patch = RegularPolygon((px, py), numVertices=6, radius=size, orientation=np.pi/6)
                patches.append(hex_patch)
                
                # Determine color
                terrain = hex_grid.terrain[y, x]
                
                if mode == "territory":
                    if (x, y) in nation_map:
                        # Nation color (with alpha for terrain hint?)
                        # Or just nation color. Let's use nation color.
                        nation = nation_map[(x, y)]
                        color = self.color_map[nation.id]
                    else:
                        # Terrain color
                        color = self.terrain_colors.get(terrain, '#000000')
                        
                elif mode == "military":
                    if (x, y) in nation_map:
                        nation = nation_map[(x, y)]
                        power = nation.get_total_military_power()
                        # Normalize power (0-100 approx range)
                        intensity = min(1.0, power / 100.0)
                        color = plt.cm.Reds(intensity)
                    else:
                        color = '#f0f0f0' # Light gray
                        if terrain == TerrainType.OCEAN: color = '#e0f0ff'
                        
                elif mode == "health":
                    if (x, y) in nation_map:
                        nation = nation_map[(x, y)]
                        health = nation.health
                        # Normalize (0-100)
                        color = plt.cm.RdYlGn(health / 100.0)
                    else:
                        color = '#f0f0f0'
                        if terrain == TerrainType.OCEAN: color = '#e0f0ff'
                
                colors.append(color)
        
        # Create collection
        p = PatchCollection(patches, match_original=True)
        # If colors are strings/tuples, we can't use array/cmap easily unless we convert
        # PatchCollection can take a list of facecolors
        p.set_facecolor(colors)
        p.set_edgecolor('none') # Remove edges for cleaner look at scale? Or thin line
        # p.set_edgecolor((0,0,0,0.1))
        
        ax.add_collection(p)
        ax.autoscale_view()
        ax.set_aspect('equal')
        ax.axis('off') # Hide axis ticks
        
        # Add title/legend
        if mode == "territory":
            ax.set_title('Territorial Control & Terrain', fontweight='bold')
            # Legend
            living = sorted([n for n in nations if n.population > 0], 
                           key=lambda n: n.gdp, reverse=True)[:10]
            legend_elements = [
                mpatches.Patch(facecolor=self.color_map[n.id], label=f"{n.name}")
                for n in living
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
            
        elif mode == "military":
            ax.set_title('Military Power Heatmap', fontweight='bold')
        elif mode == "health":
            ax.set_title('Public Health Index', fontweight='bold')

    def _plot_economic_stats(self, ax, nations: List[Nation], climate_index: float):
        """Plot economic statistics bar chart."""
        living = sorted([n for n in nations if n.population > 0], 
                       key=lambda n: n.gdp, reverse=True)[:15]
        
        if not living:
            ax.text(0.5, 0.5, 'No surviving nations', ha='center', va='center')
            ax.set_title('Economic Rankings', fontweight='bold')
            return
        
        names = [n.name[:15] for n in living]
        gdps = [n.gdp / 1e12 for n in living]
        
        bars = ax.barh(names, gdps, color=[self.color_map[n.id] for n in living])
        ax.set_xlabel('GDP (Trillions $)')
        ax.set_title(f'Top 15 Economies - Climate Index: {climate_index:.0f}', fontweight='bold')
        ax.invert_yaxis()
        
        # Add GDP values on bars
        for i, (bar, gdp) in enumerate(zip(bars, gdps)):
            ax.text(gdp, bar.get_y() + bar.get_height()/2, 
                   f'${gdp:.2f}T', va='center', ha='left', fontsize=8)
    
    def plot_timeline_analysis(self, history: List[dict], output_path: Path):
        """Generate timeline analysis plots."""
        steps = [h['step'] for h in history]
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Simulation Timeline Analysis', fontsize=16, fontweight='bold')
        
        # GDP over time
        gdps = [h['global_stats']['global_gdp'] / 1e12 for h in history]
        axes[0, 0].plot(steps, gdps, linewidth=2, color='green')
        axes[0, 0].set_title('Global GDP')
        axes[0, 0].set_xlabel('Step')
        axes[0, 0].set_ylabel('GDP (Trillions $)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Population over time
        pops = [h['global_stats']['global_population'] / 1e9 for h in history]
        axes[0, 1].plot(steps, pops, linewidth=2, color='blue')
        axes[0, 1].set_title('Global Population')
        axes[0, 1].set_xlabel('Step')
        axes[0, 1].set_ylabel('Population (Billions)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Living nations over time
        living = [h['global_stats']['living_nations'] for h in history]
        axes[1, 0].plot(steps, living, linewidth=2, color='red')
        axes[1, 0].set_title('Surviving Nations')
        axes[1, 0].set_xlabel('Step')
        axes[1, 0].set_ylabel('Number of Nations')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Climate index over time
        climate = [h['global_stats']['climate_index'] for h in history]
        axes[1, 1].plot(steps, climate, linewidth=2, color='orange')
        axes[1, 1].set_title('Climate Change Index')
        axes[1, 1].set_xlabel('Step')
        axes[1, 1].set_ylabel('Climate Index')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axhline(y=60, color='r', linestyle='--', alpha=0.5, label='Critical Threshold')
        axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()