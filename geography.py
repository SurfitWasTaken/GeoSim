import numpy as np
from enum import Enum, auto
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
import heapq
import math

class TerrainType(Enum):
    OCEAN = auto()
    PLAINS = auto()
    MOUNTAIN = auto()
    DESERT = auto()
    FOREST = auto()
    STRAIT = auto()   # Strategic narrow water passage
    CANAL = auto()    # Man-made waterway (built by high-tech nations)

@dataclass
class HexCell:
    x: int
    y: int
    terrain: TerrainType
    owner_id: Optional[int] = None
    resource_type: str = "none"
    is_capital: bool = False
    population: int = 0
    infrastructure: float = 0.0

class HexGrid:
    """
    Hexagonal grid system using offset coordinates (odd-q).
    """
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.terrain = np.full((height, width), TerrainType.OCEAN, dtype=object)
        
        # New: Object-based storage for rich data
        self.cells: Dict[Tuple[int, int], HexCell] = {}
        
        # Movement costs
        self.costs = {
            TerrainType.OCEAN: 1.0,
            TerrainType.PLAINS: 1.0,
            TerrainType.FOREST: 1.5,
            TerrainType.DESERT: 2.0,
            TerrainType.MOUNTAIN: 3.0,
            TerrainType.STRAIT: 1.0,  # Water passage
            TerrainType.CANAL: 0.8    # Efficient passage if controlled
        }
        
        # Strategic chokepoints (straits/canals)
        self.chokepoints: List[Tuple[int, int]] = []
        self.chokepoint_control: Dict[Tuple[int, int], Optional[int]] = {}
        self.blockaded_chokepoints: Set[Tuple[int, int]] = set()

    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get 6 neighbors in hex grid with toroidal wrapping."""
        # Odd-q offset directions
        # Even columns
        even_dirs = [
            (0, -1), (1, -1), (1, 0), 
            (0, 1), (-1, 0), (-1, -1)
        ]
        # Odd columns
        odd_dirs = [
            (0, -1), (1, 0), (1, 1), 
            (0, 1), (-1, 1), (-1, 0)
        ]
        
        directions = odd_dirs if x % 2 else even_dirs
        
        neighbors = []
        for dx, dy in directions:
            nx = (x + dx) % self.width
            ny = (y + dy) % self.height
            neighbors.append((nx, ny))
            
        return neighbors

    def distance(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Calculate hex distance (Manhattan distance on hex grid)."""
        # Convert to cube coordinates for accurate distance
        # This is complex on a torus, simplified heuristic for now:
        # We'll use BFS for accurate distance if needed, or simple offset distance
        # For torus, we need to check wrapped versions.
        
        dx = min(abs(x1 - x2), self.width - abs(x1 - x2))
        dy = min(abs(y1 - y2), self.height - abs(y1 - y2))
        return max(dx, dy, dx + dy) # Approximate hex distance

    def find_path(self, start: Tuple[int, int], end: Tuple[int, int], 
                 naval_capable: bool = True) -> Optional[List[Tuple[int, int]]]:
        """A* pathfinding."""
        def heuristic(a, b):
            return self.distance(a[0], a[1], b[0], b[1])

        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}
        
        while frontier:
            current = heapq.heappop(frontier)[1]
            
            if current == end:
                break
            
            for next_node in self.get_neighbors(*current):
                terrain = self.terrain[next_node[1], next_node[0]]
                
                # Impassable check
                if not naval_capable and terrain == TerrainType.OCEAN:
                    continue
                
                new_cost = cost_so_far[current] + self.costs.get(terrain, 1.0)
                
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + heuristic(end, next_node)
                    heapq.heappush(frontier, (priority, next_node))
                    came_from[next_node] = current
                    
        if end not in came_from:
            return None
            
        # Reconstruct path
        path = []
        curr = end
        while curr != start:
            path.append(curr)
            curr = came_from[curr]
        path.append(start)
        path.reverse()
        return path

    def generate_terrain(self, seed: int = None):
        """Generate terrain using noise (simulated)."""
        if seed:
            np.random.seed(seed)
            
        # Simple generation: Blobs
        # 1. Ocean base
        # 2. Continents (Plains)
        # 3. Features (Mountains, Deserts)
        
        # Random walk for continents
        num_continents = 5
        for _ in range(num_continents):
            cx, cy = np.random.randint(0, self.width), np.random.randint(0, self.height)
            size = np.random.randint(50, 200)
            
            curr_x, curr_y = cx, cy
            for _ in range(size):
                self.terrain[curr_y, curr_x] = TerrainType.PLAINS
                neighbors = self.get_neighbors(curr_x, curr_y)
                curr_x, curr_y = neighbors[np.random.randint(0, len(neighbors))]
                
        # Add mountains and deserts
        for y in range(self.height):
            for x in range(self.width):
                if self.terrain[y, x] == TerrainType.PLAINS:
                    r = np.random.random()
                    if r < 0.1:
                        self.terrain[y, x] = TerrainType.MOUNTAIN
                    elif r < 0.2:
                        self.terrain[y, x] = TerrainType.FOREST
                    elif r < 0.25:
                        self.terrain[y, x] = TerrainType.DESERT
        
        # Generate strategic straits (chokepoints)
        # Find narrow ocean passages between land masses
        self._generate_straits()
    
    def _generate_straits(self):
        """Identify and mark strategic strait chokepoints."""
        # Strategy: Find ocean tiles that connect two large ocean regions
        # and are adjacent to land on both sides (narrow passages)
        
        for y in range(self.height):
            for x in range(self.width):
                if self.terrain[y, x] == TerrainType.OCEAN:
                    neighbors = self.get_neighbors(x, y)
                    
                    # Count land vs ocean neighbors
                    land_neighbors = sum(1 for nx, ny in neighbors 
                                        if self.terrain[ny, nx] not in [TerrainType.OCEAN, TerrainType.STRAIT])
                    ocean_neighbors = sum(1 for nx, ny in neighbors 
                                         if self.terrain[ny, nx] == TerrainType.OCEAN)
                    
                    # Strait criteria: 2-4 land neighbors (narrow passage)
                    if 2 <= land_neighbors <= 4 and ocean_neighbors >= 2:
                        # Random chance to make it a strategic strait
                        if np.random.random() < 0.3:
                            self.terrain[y, x] = TerrainType.STRAIT
                            self.chokepoints.append((x, y))
                            self.chokepoint_control[(x, y)] = None  # Initially uncontrolled

        # Populate cell objects
        for y in range(self.height):
            for x in range(self.width):
                self.cells[(y, x)] = HexCell(x, y, self.terrain[y, x])
