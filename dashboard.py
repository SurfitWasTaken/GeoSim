"""
Interactive Dashboard module for GeoSim.
Focuses on real-time metrics, rankings, and event feeds.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import List, Dict, Any
import numpy as np
from pathlib import Path

from nation import Nation
from config import SimulationConfig

class Dashboard:
    def __init__(self, config: SimulationConfig):
        self.config = config
        plt.style.use('dark_background')
        
    def create_realtime_dashboard(self, step: int, nations: List[Nation], 
                                  global_stats: Dict, events: List[str], output_path: Path):
        """
        Create a 6-panel real-time dashboard.
        1. Global Overview
        2. Top 5 Powers
        3. Event Feed
        4. Alliance/Trade Network (Placeholder or integration)
        5. Resource Watch
        6. Crisis Indicators
        """
        fig = plt.figure(figsize=(20, 12), facecolor='#1a1a1a')
        gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1], hspace=0.3, wspace=0.2)
        
        # 1. Global Overview (Top Left)
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_global_overview(ax1, global_stats)
        
        # 2. Top Powers (Top Center)
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_top_powers(ax2, nations)
        
        # 3. Event Feed (Top Right)
        ax3 = fig.add_subplot(gs[0, 2])
        self._render_event_feed(ax3, events)
        
        # 4. Resource Watch (Bottom Left)
        ax4 = fig.add_subplot(gs[1, 0])
        self._plot_resource_watch(ax4, nations)
        
        # 5. Crisis Indicators (Bottom Center)
        ax5 = fig.add_subplot(gs[1, 1])
        self._plot_crisis_indicators(ax5, nations)
        
        # 6. Future / Extra (Bottom Right)
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.text(0.5, 0.5, "Network Visualization\n(See network_viz.py)", 
                 ha='center', va='center', color='#555555')
        ax6.set_title("Network Analysis", color='white')
        ax6.axis('off')

        fig.suptitle(f"GeoSim Command Dashboard - Step {step}", fontsize=24, color='white', fontweight='bold')
        
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close(fig)

    def _plot_global_overview(self, ax, stats: Dict):
        """Plot key global metrics."""
        ax.set_title("Global Overview", color='#44FF88', fontweight='bold')
        ax.axis('off')
        
        # Text-based metrics for now, or sparklines if history available
        gdp = stats.get('global_gdp', 0) / 1e12
        pop = stats.get('global_population', 0) / 1e9
        wars = stats.get('active_wars_count', 0)
        temp = stats.get('climate_index', 0)
        
        metrics = [
            f"Global GDP: ${gdp:.2f}T",
            f"Population: {pop:.2f}B",
            f"Active Wars: {wars}",
            f"Temp Anomaly: +{temp:.2f}°C"
        ]
        
        y = 0.8
        for m in metrics:
            ax.text(0.1, y, m, fontsize=14, color='white')
            y -= 0.15

    def _plot_top_powers(self, ax, nations: List[Nation]):
        """Rank top nations by score."""
        ax.set_title("Superpower Rankings", color='#4488FF', fontweight='bold')
        ax.axis('off')
        
        # Score = GDP + Military + Tech
        sorted_nations = sorted(nations, key=lambda n: n.gdp, reverse=True)[:5]
        
        y = 0.8
        ax.text(0.05, 0.9, "Rank   Nation          GDP      Tech", color='#888888', fontsize=10)
        
        for i, n in enumerate(sorted_nations):
            gdp_str = f"${n.gdp/1e12:.1f}T"
            entry = f"#{i+1}      {n.name[:12]:<12}  {gdp_str:<7}  {n.technology:.0f}"
            ax.text(0.05, y, entry, fontsize=12, color='white', fontfamily='monospace')
            y -= 0.12

    def _render_event_feed(self, ax, events: List[str]):
        """Render scrolling event log."""
        ax.set_title("Global Event Feed", color='#FFAA00', fontweight='bold')
        ax.axis('off')
        ax.set_facecolor('#222222')
        
        # Show last 10 events
        recent = events[-10:] if events else ["No recent events"]
        
        y = 0.9
        for e in reversed(recent):
            col = 'white'
            if "WAR" in e: col = '#FF4444'
            elif "CRISIS" in e: col = '#FF8800'
            elif "ALLIANCE" in e: col = '#44FF88'
            
            ax.text(0.05, y, f"• {e[:40]}...", fontsize=10, color=col)
            y -= 0.08

    def _plot_resource_watch(self, ax, nations: List[Nation]):
        """Visualise resource control."""
        ax.set_title("Strategic Resource Control", color='#FF00FF', fontweight='bold')
        
        # Aggregate logic
        total_oil = sum(n.resources.get('oil', 0) for n in nations)
        total_rare = sum(n.resources.get('rare_earth', 0) for n in nations)
        
        if total_oil == 0: total_oil = 1
        
        # Top 3 oil controllers
        top_oil = sorted(nations, key=lambda n: n.resources.get('oil', 0), reverse=True)[:3]
        labels = [n.name for n in top_oil] + ['Others']
        sizes = [n.resources.get('oil', 0) for n in top_oil]
        sizes.append(total_oil - sum(sizes))
        
        # Pie chart
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
               colors=['#FFD700', '#C0C0C0', '#CD7F32', '#555555'],
               textprops={'color': 'white'})

    def _plot_crisis_indicators(self, ax, nations: List[Nation]):
        """Gauges for instability."""
        ax.set_title("Global instability Index", color='#FF4444', fontweight='bold')
        
        avg_stability = np.mean([n.stability for n in nations]) if nations else 0
        debt_crisis_count = sum(1 for n in nations if n.in_default)
        avg_exhaustion = np.mean([n.war_exhaustion for n in nations]) if nations else 0
        
        # Bar chart
        metrics = ['Avg Stability', 'Debt Crises', 'Avg Exhaustion']
        vals = [avg_stability, debt_crisis_count * 10, avg_exhaustion] # Scale for vis
        colors = ['#44FF44' if avg_stability > 50 else '#FF4444', 
                 '#FF4444', 
                 '#FFAA00']
        
        ax.bar(metrics, vals, color=colors)
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.2)
