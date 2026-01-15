"""
Visualization module for creating world maps and charts.
Generates matplotlib-based visual representations of simulation state.
Promoted to Priority 4: Enhanced Visualization System.
"""

from typing import List, Tuple, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import RegularPolygon, Circle
from matplotlib.collections import PatchCollection, LineCollection
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
from pathlib import Path
import math

from nation import Nation
from config import SimulationConfig
from geography import HexGrid, TerrainType


class Visualizer:
    """
    Handles all visualization and plotting.
    Priority 4 Upgrade: Premium aesthetics, 3x3 information grid, dark theme.
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.color_map = {}
        self._generate_colors()
        
        # Terrain colors (Enhanced Palette)
        self.terrain_colors = {
            TerrainType.OCEAN: '#0F1E3D',    # Deep Dark Blue/Navy
            TerrainType.PLAINS: '#2D3E2E',   # Muted Dark Green
            TerrainType.FOREST: '#1A291A',   # Deep Forest Green
            TerrainType.DESERT: '#5C4033',   # Dark Sand/Brown
            TerrainType.MOUNTAIN: '#4A4A4A', # Dark Gray
            TerrainType.STRAIT: '#1C3969',   # Lighter Deep Blue
            TerrainType.CANAL: '#008B8B'     # Dark Cyan
        }
    
    def _generate_colors(self):
        """Generate distinct, premium pastel/neon colors for each nation."""
        np.random.seed(42)  # Consistent colors
        # Use a qualitative colormap like 'tab20' or 'Set3' but adjusted for dark theme
        cmap = plt.get_cmap('tab20')
        for i in range(self.config.num_nations):
            self.color_map[i] = cmap(i % 20)
    
    def create_world_map(self, hex_grid: HexGrid, nations: List[Nation], output_path: Path, active_wars: List[Dict]):
        """
        Create comprehensive world map showing multiple layers of information.
        Upgrade: 3x3 Grid of premium visualizations.
        """
        # Set dark style
        plt.style.use('dark_background')
        
        fig = plt.figure(figsize=(24, 18), facecolor='#1a1a1a')
        # 3x3 Grid
        # 1. Political (Main)   2. Economic Heat    3. Tech Level
        # 4. Military Power     5. Inequality       6. Resources 
        # 7. Alliances          8. Conflicts        9. Climate/Health
        
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        axes = [fig.add_subplot(gs[i, j]) for i in range(3) for j in range(3)]
        
        nations_dict = {n.id: n for n in nations}
        
        # 1. Political Map (Main)
        self._plot_political_map(axes[0], hex_grid, nations_dict, "Political & Territory")
        
        # 2. Economic Power (GDP)
        self._plot_heatmap(axes[1], hex_grid, nations_dict, "gdp", "Economic Power (GDP)", cm.plasma)
        
        # 3. Technology Level
        self._plot_heatmap(axes[2], hex_grid, nations_dict, "technology", "Technology Level", cm.viridis)
        
        # 4. Military Strength
        self._plot_heatmap(axes[3], hex_grid, nations_dict, "total_military", "Military Strength", cm.magma)
        
        # 5. Inequality (Gini)
        self._plot_heatmap(axes[4], hex_grid, nations_dict, "domestic_gini", "Inequality (Gini)", cm.RdYlGn_r)
        
        # 6. Strategic Resources
        self._plot_resources(axes[5], hex_grid, nations_dict, "Resource Distribution")
        
        # 7. Alliance Network (Network Graph overlay on map space roughly)
        # Note: Mapping network to hex grid is tricky, we'll show alliance blocs using map coloring
        self._plot_alliances_map(axes[6], hex_grid, nations_dict, "Diplomatic Blocs")
        
        # 8. Active Conflicts
        self._plot_conflicts(axes[7], hex_grid, nations_dict, active_wars, "Active Conflicts")
        
        # 9. Stability/Unrest
        self._plot_heatmap(axes[8], hex_grid, nations_dict, "stability", "Domestic Stability", cm.coolwarm)
        
        # Global Stats Title
        total_gdp = sum(n.gdp for n in nations) / 1e12
        total_pop = sum(n.population for n in nations) / 1e6
        step_num = int(output_path.stem.split('_')[-1]) if '_' in output_path.stem else 0
        
        fig.suptitle(f"GeoSim Global State - Step {step_num}\nGDP: ${total_gdp:.1f}T | Pop: {total_pop:.0f}M | Wars: {len(active_wars)}", 
                     fontsize=24, color='white', fontweight='bold', y=0.95)
        
        # Save
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close(fig)

    def _draw_hex_base(self, ax, hex_grid: HexGrid, title: str):
        """Helper to draw the base hex grid with terrain."""
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=14, color='white', pad=10)
        ax.axis('off')
        
        patches = []
        colors = []
        
        for r, q in hex_grid.cells:
            cell = hex_grid.cells[(r, q)]
            x, y = self._hex_to_pixel(q, r)
            poly = RegularPolygon((x, y), numVertices=6, radius=1.0, orientation=np.radians(30))
            patches.append(poly)
            # Default to terrain color
            colors.append(self.terrain_colors.get(cell.terrain, '#000000'))
            
        collection = PatchCollection(patches, match_original=True)
        collection.set_facecolors(colors)
        collection.set_edgecolor('#111111') # Dark borders for detailed grid
        collection.set_linewidth(0.2)
        ax.add_collection(collection)
        
        # Set limits
        w = hex_grid.width
        h = hex_grid.height
        ax.set_xlim(-2, w * 1.8) # Approx scaling
        ax.set_ylim(-2, h * 1.6)
        
        return patches # Return bases to potentially update

    def _plot_political_map(self, ax, hex_grid: HexGrid, nations_dict: Dict[int, Nation], title: str):
        """Draw political borders and fills."""
        patches = []
        colors = []
        
        for r, q in hex_grid.cells:
            cell = hex_grid.cells[(r, q)]
            x, y = self._hex_to_pixel(q, r)
            poly = RegularPolygon((x, y), numVertices=6, radius=1.0, orientation=np.radians(30))
            patches.append(poly)
            
            if cell.owner_id is not None and cell.owner_id in nations_dict:
                # Use nation color
                base_color = np.array(self.color_map[cell.owner_id])
                # Capital check
                if cell.is_capital:
                    colors.append(np.clip(base_color + 0.2, 0, 1)) # Brighter for capital
                else:
                    colors.append(base_color)
            else:
                colors.append(self.terrain_colors.get(cell.terrain, '#000000'))
        
        collection = PatchCollection(patches)
        collection.set_facecolors(colors)
        collection.set_edgecolor('#1a1a1a')
        collection.set_linewidth(0.1)
        ax.add_collection(collection)
        
        # Add capital markers
        for nid, nation in nations_dict.items():
            if not nation.capital_loc: continue
            q, r = nation.capital_loc
            if (r, q) in hex_grid.cells:
                 x, y = self._hex_to_pixel(q, r)
                 ax.text(x, y, "★", color='white', ha='center', va='center', fontsize=8, fontweight='bold')
                 # Country Label
                 ax.text(x, y+1.5, nation.name[:3], color='white', ha='center', fontsize=6, alpha=0.8)

        self._finalize_ax(ax, hex_grid, title)

    def _plot_heatmap(self, ax, hex_grid: HexGrid, nations_dict: Dict[int, Nation], stat_key: str, title: str, cmap):
        """Generic nation-level heatmap."""
        patches = []
        values = []
        
        # Get value range for normalization
        nation_vals = []
        for n in nations_dict.values():
            if stat_key == "total_military":
                nation_vals.append(n.get_total_military_power())
            elif hasattr(n, stat_key):
                nation_vals.append(getattr(n, stat_key))
            else:
                nation_vals.append(0)
                
        if not nation_vals: nation_vals = [0]
        vmin, vmax = min(nation_vals), max(nation_vals)
        if vmin == vmax: vmax += 1
        
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        
        for r, q in hex_grid.cells:
            cell = hex_grid.cells[(r, q)]
            x, y = self._hex_to_pixel(q, r)
            
            poly = RegularPolygon((x, y), numVertices=6, radius=1.0, orientation=np.radians(30))
            patches.append(poly)
            
            val = 0
            if cell.owner_id is not None and cell.owner_id in nations_dict:
                 n = nations_dict[cell.owner_id]
                 if stat_key == "total_military":
                     val = n.get_total_military_power()
                 else:
                     val = getattr(n, stat_key, 0)
                 color = cmap(norm(val))
                 values.append(color)
            else:
                 # Dark terrain for non-owned
                 values.append('#111111')

        collection = PatchCollection(patches)
        collection.set_facecolors(values)
        ax.add_collection(collection)
        self._finalize_ax(ax, hex_grid, title)
        
        # Colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.tick_params(labelsize=6, colors='white')

    def _plot_resources(self, ax, hex_grid: HexGrid, nations_dict: Dict, title: str):
        """Map showing key resources."""
        self._draw_hex_base(ax, hex_grid, title)
        
        # Overlay resource icons
        for (r, q), cell in hex_grid.cells.items():
            if cell.resource_type != "none":
                x, y = self._hex_to_pixel(q, r)
                color = '#FFD700' if cell.resource_type == 'gold' else \
                        '#000000' if cell.resource_type == 'oil' else \
                        '#8A2BE2' if cell.resource_type == 'rare_earth' else 'white'
                marker = 'o' if cell.resource_type == 'oil' else \
                         'd' if cell.resource_type == 'rare_earth' else '*'
                
                ax.scatter(x, y, c=color, marker=marker, s=15, edgecolors='white', linewidth=0.5, zorder=10)

    def _plot_alliances_map(self, ax, hex_grid: HexGrid, nations_dict: Dict, title: str):
        """Map coloring nations by their alliance bloc leader."""
        patches = []
        colors = []
        
        # Simple heuristic: color by lowest ID in alliance network for visualization
        # In full implementation, would use graph community detection
        
        for r, q in hex_grid.cells:
            cell = hex_grid.cells[(r, q)]
            x, y = self._hex_to_pixel(q, r)
            poly = RegularPolygon((x, y), numVertices=6, radius=1.0, orientation=np.radians(30))
            patches.append(poly)
            
            if cell.owner_id is not None and cell.owner_id in nations_dict:
                n = nations_dict[cell.owner_id]
                # Determine 'color identity' by alliance
                # Use own color if no alliances, else average of allies? 
                # Simplest: if allied, use leader color (lowest ID)
                if n.alliances:
                    bloc_id = min(list(n.alliances) + [n.id])
                    colors.append(self.color_map[bloc_id])
                else:
                     colors.append(self.color_map[n.id])
            else:
                colors.append('#111111')
                
        collection = PatchCollection(patches)
        collection.set_facecolors(colors)
        collection.set_alpha(0.8)
        ax.add_collection(collection)
        self._finalize_ax(ax, hex_grid, title)

    def _plot_conflicts(self, ax, hex_grid: HexGrid, nations_dict: Dict, active_wars: List[Dict], title: str):
        """Map highlighting nations at war."""
        self._draw_hex_base(ax, hex_grid, title)
        
        warring_nations = set()
        for war in active_wars:
            warring_nations.add(war['attacker_id'])
            warring_nations.add(war['defender_id'])
            warring_nations.update(war.get('attacker_allies', []))
            warring_nations.update(war.get('defender_allies', []))
            
        patches = []
        colors = []
        
        for r, q in hex_grid.cells:
            cell = hex_grid.cells[(r, q)]
            x, y = self._hex_to_pixel(q, r)
            poly = RegularPolygon((x, y), numVertices=6, radius=1.0, orientation=np.radians(30))
            patches.append(poly)
            
            if cell.owner_id in warring_nations:
                colors.append('#FF4444') # Red for war
            elif cell.owner_id is not None:
                colors.append('#444444') # Grey for Neutral
            else:
                 colors.append('#222222')
                 
        collection = PatchCollection(patches)
        collection.set_facecolors(colors)
        ax.add_collection(collection)
        
        # Draw crossed swords or explosion markers at capitals of warring nations
        for nid in warring_nations:
            if nid in nations_dict:
                n = nations_dict[nid]
                if n.capital_loc:
                     q, r = n.capital_loc
                     x, y = self._hex_to_pixel(q, r)
                     ax.text(x, y, "⚔️", color='yellow', ha='center', va='center', fontsize=12)

    def _finalize_ax(self, ax, hex_grid, title):
        """Standardize axes limits and removal."""
        w = hex_grid.width
        h = hex_grid.height
        ax.set_xlim(-2, w * 1.8)
        ax.set_ylim(-2, h * 1.6)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=10, color='white', pad=5)

    def _hex_to_pixel(self, q, r):
        """Convert axial hex coordinates to pixel (x, y)."""
        x = np.sqrt(3) * q + np.sqrt(3)/2 * r
        y = 1.5 * r
        return x, y
        
    def plot_timeline_analysis(self, history: List[dict], output_path: Path):
        """
        Generate timeline analysis plots showing global trends.
        Upgrade: 6-panel layout with dark theme.
        """
        plt.style.use('dark_background')
        
        steps = [h['step'] for h in history]
        
        # Extract data
        gdps = [h['global_stats']['global_gdp'] / 1e12 for h in history]
        pops = [h['global_stats']['global_population'] / 1e9 for h in history]
        living = [h['global_stats']['living_nations'] for h in history]
        climate = [h['global_stats']['climate_index'] for h in history]
        gini = [h['global_stats'].get('gini_coefficient', 0.0) for h in history]
        wars_count = [h['global_stats'].get('active_wars_count', 0) for h in history]
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10), facecolor='#1a1a1a')
        fig.suptitle('GeoSim Simulation Trends', fontsize=20, fontweight='bold', color='white', y=0.95)
        
        # 1. Global GDP
        ax = axes[0, 0]
        ax.plot(steps, gdps, linewidth=2, color='#00FF00') # Neon Green
        ax.fill_between(steps, gdps, color='#00FF00', alpha=0.1)
        ax.set_title('Global GDP (Trillions $)', color='white')
        ax.grid(True, alpha=0.1)
        
        # 2. Population
        ax = axes[0, 1]
        ax.plot(steps, pops, linewidth=2, color='#00FFFF') # Cyan
        ax.set_title('Global Population (Billions)', color='white')
        ax.grid(True, alpha=0.1)
        
        # 3. Climate
        ax = axes[0, 2]
        ax.plot(steps, climate, linewidth=2, color='#FF4444') # Red
        ax.set_title('Avg Temp Rise (°C)', color='white')
        ax.axhline(y=2.0, color='orange', linestyle='--', alpha=0.5, label='Paris Target')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.1)
        
        # 4. Active Wars
        ax = axes[1, 0]
        ax.bar(steps, wars_count, color='#FF0000', alpha=0.7)
        ax.set_title('Active Wars', color='white')
        ax.grid(True, alpha=0.1)
        
        # 5. Inequality (Gini)
        ax = axes[1, 1]
        ax.plot(steps, gini, linewidth=2, color='#FFFF00') # Yellow
        ax.set_title('Global Inequality (Gini)', color='white')
        ax.set_ylim(0.2, 0.8)
        ax.axhline(y=0.4, color='#FF8800', linestyle='--', alpha=0.5, label='Warning Level')
        ax.grid(True, alpha=0.1)
        
        # 6. Surviving Nations
        ax = axes[1, 2]
        ax.plot(steps, living, linewidth=2, color='#FF00FF') # Magenta
        ax.set_title('Surviving Nations', color='white')
        ax.grid(True, alpha=0.1)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close(fig)