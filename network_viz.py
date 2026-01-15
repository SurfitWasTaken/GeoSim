"""
Network visualization module for trade and alliance graphs.
"""

import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import numpy as np
from pathlib import Path

from nation import Nation
from config import SimulationConfig

class NetworkVisualizer:
    def __init__(self, config: SimulationConfig):
        self.config = config
        plt.style.use('dark_background')

    def create_trade_network(self, nations: List[Nation], trade_volumes: Dict[Tuple[int, int], float], output_path: Path):
        """
        Visualize global trade network.
        Nodes: Nations (size=GDP)
        Edges: Trade volume
        """
        G = nx.DiGraph()
        
        # Add nodes
        for n in nations:
            if n.population > 0:
                G.add_node(n.id, label=n.name, gdp=n.gdp, tech=n.technology)
                
        # Add edges
        if trade_volumes:
            max_vol = max(trade_volumes.values()) if trade_volumes else 1.0
            for (n1, n2), vol in trade_volumes.items():
                if vol > max_vol * 0.05: # Only show significant trade > 5% of max
                    if n1 in G.nodes and n2 in G.nodes:
                        G.add_edge(n1, n2, weight=vol)
        
        plt.figure(figsize=(12, 12), facecolor='#1a1a1a')
        
        # Layout
        pos = nx.spring_layout(G, k=0.5, seed=42)
        
        # Draw nodes
        node_sizes = [nx.get_node_attributes(G, 'gdp')[n] / 1e11 for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='#4488FF', alpha=0.8)
        
        # Draw edges
        edges = G.edges()
        if edges:
            weights = [G[u][v]['weight'] for u, v in edges]
            # Normalize weights for width
            width = [max(0.1, (w / max(weights)) * 5) for w in weights]
            nx.draw_networkx_edges(G, pos, width=width, edge_color='#44FF88', alpha=0.3, arrows=True)
            
        # Labels
        nx.draw_networkx_labels(G, pos, font_size=8, font_color='white')
        
        plt.title("Global Trade Network", color='white', fontsize=16)
        plt.axis('off')
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close()

    def create_alliance_network(self, nations: List[Nation], output_path: Path):
        """
        Visualize alliance blocs.
        """
        G = nx.Graph()
        
        for n in nations:
            if n.population > 0:
                G.add_node(n.id, label=n.name)
                for ally_id in n.alliances:
                    if ally_id > n.id: # Avoid duplicates
                         G.add_edge(n.id, ally_id)
                         
        plt.figure(figsize=(10, 10), facecolor='#1a1a1a')
        pos = nx.kamada_kawai_layout(G)
        
        nx.draw_networkx_nodes(G, pos, node_color='#FFDD44', node_size=500)
        nx.draw_networkx_edges(G, pos, edge_color='white', alpha=0.5)
        nx.draw_networkx_labels(G, pos, font_color='black', font_size=8)
        
        plt.title("Strategic Alliance Blocs", color='white')
        plt.axis('off')
        plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='#1a1a1a')
        plt.close()
