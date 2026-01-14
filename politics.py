from enum import Enum, auto
from typing import List, Dict, Optional
import random
from dataclasses import dataclass

class FactionType(Enum):
    MILITARY = auto()
    CORPORATE = auto()
    POPULIST = auto()
    LIBERAL = auto()
    CONSERVATIVE = auto()
    GREEN = auto()

@dataclass
class Faction:
    name: str
    type: FactionType
    influence: float = 0.0 # 0-100: Power to shape policy
    loyalty: float = 50.0  # 0-100: Risk of coup/rebellion
    demands: List[str] = None
    
    def __post_init__(self):
        if self.demands is None:
            self.demands = []

class PoliticalSystem:
    """
    Manages domestic politics, factions, and stability.
    """
    def __init__(self, nation):
        self.nation = nation
        self.factions: List[Faction] = []
        self._initialize_factions()
        
    def _initialize_factions(self):
        """Create factions based on government type and ideology."""
        # Every nation has Military and Corporate
        self.factions.append(Faction("Armed Forces", FactionType.MILITARY, influence=30, loyalty=70))
        self.factions.append(Faction("Business Council", FactionType.CORPORATE, influence=30, loyalty=60))
        
        # Ideological factions
        if self.nation.ideology > 20:
            self.factions.append(Faction("Progressive Union", FactionType.LIBERAL, influence=20, loyalty=50))
        elif self.nation.ideology < -20:
            self.factions.append(Faction("Traditionalist Front", FactionType.CONSERVATIVE, influence=20, loyalty=50))
        else:
            self.factions.append(Faction("People's Party", FactionType.POPULIST, influence=20, loyalty=50))
            
        # Green faction for high-tech/aware nations
        if random.random() < 0.5:
             self.factions.append(Faction("Eco-Guard", FactionType.GREEN, influence=10, loyalty=60))
             
        self._normalize_influence()

    def _normalize_influence(self):
        """Ensure influence sums to 100."""
        total = sum(f.influence for f in self.factions)
        if total > 0:
            for f in self.factions:
                f.influence = (f.influence / total) * 100.0

    def update(self):
        """Update faction loyalty and check for demands."""
        for faction in self.factions:
            # Loyalty drift based on nation state
            
            # Military likes high spending and war
            if faction.type == FactionType.MILITARY:
                mil_spend = self.nation.budget.get("military", 0.0)
                if mil_spend > 0.05: faction.loyalty += 1
                elif mil_spend < 0.02: faction.loyalty -= 1
                
            # Corporate likes stability and trade
            elif faction.type == FactionType.CORPORATE:
                if self.nation.stability > 70: faction.loyalty += 0.5
                if self.nation.trade_balance > 0: faction.loyalty += 0.5
                
            # Populists hate inequality (simplified as low stability/health)
            elif faction.type == FactionType.POPULIST:
                if self.nation.health < 50: faction.loyalty -= 1
                
            # Green likes climate action (low carbon intensity?)
            # Simplified: Random drift for now
            
            # Clamp
            faction.loyalty = max(0.0, min(100.0, faction.loyalty))
            
    def check_coup_risk(self) -> bool:
        """Check if any powerful faction is disloyal enough to coup."""
        for faction in self.factions:
            # High influence + Low loyalty = Danger
            if faction.influence > 40 and faction.loyalty < 20:
                # Coup attempt probability
                if random.random() < 0.1:
                    return True
        return False
