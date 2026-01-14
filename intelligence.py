from enum import Enum, auto
from typing import List, Dict, Optional
import random
from dataclasses import dataclass

class MissionType(Enum):
    STEAL_TECH = auto()
    RIG_ELECTION = auto()
    SABOTAGE_INFRASTRUCTURE = auto()
    ASSASSINATE = auto()
    INCITE_UNREST = auto()

@dataclass
class Operation:
    type: MissionType
    target_id: int
    success_prob: float
    attribution_risk: float

class SpyAgency:
    """
    Manages intelligence operations and covert actions.
    """
    def __init__(self, nation):
        self.nation = nation
        # Budget scales with GDP (0.1-0.5% of GDP)
        self.budget: float = max(1e9, nation.gdp * 0.002)  # 0.2% default
        self.operatives: int = 100
        self.tech_level: float = nation.technology  # Use nation's tech
        
    def conduct_operation(self, target, mission_type: MissionType) -> Dict:
        """
        Attempt a covert operation.
        Returns dict with 'success' (bool) and 'detected' (bool).
        """
        # Base probability
        prob = 0.5
        
        # Tech advantage (more important)
        tech_diff = self.tech_level - target.technology
        prob += tech_diff * 0.015  # Increased from 0.01
        
        # Budget factor
        budget_factor = min(2.0, self.budget / 1e9)
        prob *= budget_factor
        
        # Counter-intelligence (Target stability/tech)
        defense = (target.stability + target.technology) / 200.0
        prob *= (1.0 - defense * 0.8)  # Stronger defense impact
        
        # Mission difficulty
        if mission_type == MissionType.ASSASSINATE: prob *= 0.15
        elif mission_type == MissionType.RIG_ELECTION: prob *= 0.3
        elif mission_type == MissionType.STEAL_TECH: prob *= 0.6
        elif mission_type == MissionType.SABOTAGE_INFRASTRUCTURE: prob *= 0.5
        elif mission_type == MissionType.INCITE_UNREST: prob *= 0.4
        
        success = random.random() < max(0.05, min(0.95, prob))
        
        # Detection risk
        # Failed missions are much easier to detect
        detect_prob = 0.3 if success else 0.7  # Increased from 0.2/0.5
        detect_prob *= (1.0 - self.tech_level / 200.0)  # Better tech hides tracks
        
        detected = random.random() < max(0.05, min(0.95, detect_prob))
        
        # Apply effects if successful
        if success:
            if mission_type == MissionType.STEAL_TECH:
                # Tech theft provides 5-10% of gap
                tech_gap = max(0, target.technology - self.nation.technology)
                tech_gain = tech_gap * random.uniform(0.05, 0.10)
                self.nation.technology += tech_gain
            elif mission_type == MissionType.SABOTAGE_INFRASTRUCTURE:
                # Sabotage scales with target GDP (0.5-2% damage)
                damage_pct = random.uniform(0.005, 0.02)
                target.gdp *= (1 - damage_pct)
            elif mission_type == MissionType.INCITE_UNREST:
                target.stability -= random.uniform(5, 15)
        
        return {
            "success": success,
            "detected": detected,
            "type": mission_type
        }
        
    def upgrade(self):
        """Invest in agency capabilities."""
        cost = self.nation.gdp * 0.005  # 0.5% of GDP
        if self.nation.gdp > cost * 20:  # Affordable
            self.nation.gdp -= cost
            self.budget += cost * 0.5
            self.tech_level = min(100, self.tech_level + 0.5)
            self.operatives += 10
