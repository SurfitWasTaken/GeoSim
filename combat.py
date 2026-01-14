"""
Military conflict resolution using Lanchester equations.
Models warfare with realistic factors: tech, logistics, nuclear weapons, and war exhaustion.
"""

from typing import List, Dict, Tuple, Optional
import random
import numpy as np

from nation import Nation
from config import SimulationConfig


class WarSystem:
    """Manages military conflicts between nations."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.active_wars: List[Dict] = []
        self.war_history: List[Dict] = []
        self.nuclear_detonations = 0
    
    def check_war_triggers(self, nations: List[Nation]) -> List[Tuple[int, int, str]]:
        """
        Check for war triggers between nations.
        Returns list of (attacker_id, defender_id, cause).
        """
        wars = []
        
        for i, attacker in enumerate(nations):
            if attacker.population == 0 or attacker.is_at_war:
                continue
            
            # War exhaustion prevents immediate re-engagement
            if attacker.war_exhaustion > 50:
                continue
            
            for j, defender in enumerate(nations[i+1:], start=i+1):
                if defender.population == 0 or defender.is_at_war:
                    continue
                
                # Skip if allied
                if attacker.id in defender.alliances:
                    continue
                
                # Calculate war probability
                war_prob = self._calculate_war_probability(attacker, defender)
                
                if random.random() < war_prob:
                    cause = self._determine_war_cause(attacker, defender)
                    wars.append((attacker.id, defender.id, cause))
        
        return wars
    
    def _calculate_war_probability(self, attacker: Nation, defender: Nation) -> float:
        """Calculate probability of war initiation."""
        base_prob = self.config.war_base_probability
        
        # Ideological differences
        ideology_factor = abs(attacker.ideology - defender.ideology) * self.config.war_ideology_factor
        
        # Resource competition
        resource_factor = 0
        for resource in ["oil", "rare_earth"]:
            if defender.resources.get(resource, 0) > attacker.resources.get(resource, 0) * 2:
                resource_factor += self.config.war_resource_factor
        
        # Power imbalance (strong nations attack weak ones)
        power_ratio = attacker.get_total_military_power() / max(1, defender.get_total_military_power())
        power_factor = 0.01 if power_ratio > 2 else 0
        
        # Government type modifiers (democracies less likely to attack)
        gov_modifier = 1 - (self.config.realism_level == "high" and 
                           attacker.government_type == "Democracy" and 
                           defender.government_type == "Democracy") * 0.8  # Democratic peace theory
        
        # Economic factors (poor nations more aggressive)
        economic_desperation = max(0, (30000 - attacker.get_gdp_per_capita()) / 30000) * 0.01
        
        total_prob = (base_prob + ideology_factor + resource_factor + 
                     power_factor + economic_desperation) * gov_modifier
        
        return min(0.15, total_prob)  # Cap at 15% per year
    
    def _determine_war_cause(self, attacker: Nation, defender: Nation) -> str:
        """Determine the casus belli for war."""
        causes = []
        
        if abs(attacker.ideology - defender.ideology) > 60:
            causes.append("ideological")
        
        if any(defender.resources.get(r, 0) > attacker.resources.get(r, 0) * 1.5 
               for r in ["oil", "rare_earth"]):
            causes.append("resources")
        
        if defender.id in attacker.sanctions_from:
            causes.append("sanctions")
        
        if len(defender.alliances) > len(attacker.alliances) + 3:
            causes.append("preemptive")
        
        if not causes:
            causes.append("border_dispute")
        
        return random.choice(causes)
    
    def initiate_war(self, attacker_id: int, defender_id: int, 
                    cause: str, nations: List[Nation]) -> str:
        """Initiate military conflict."""
        attacker = nations[attacker_id]
        defender = nations[defender_id]
        
        attacker.is_at_war = True
        defender.is_at_war = True
        
        war = {
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "attacker_allies": list(attacker.alliances),
            "defender_allies": list(defender.alliances),
            "cause": cause,
            "duration": 0,
            "intensity": random.uniform(0.5, 1.0)
        }
        
        self.active_wars.append(war)
        
        return f"WAR: {attacker.name} attacks {defender.name} over {cause}"
    
    def resolve_wars(self, nations: List[Nation]) -> List[str]:
        """Resolve all active wars using combat resolution."""
        events = []
        nations_dict = {n.id: n for n in nations}
        
        for war in self.active_wars[:]:
            war["duration"] += 1
            
            attacker = nations_dict.get(war["attacker_id"])
            defender = nations_dict.get(war["defender_id"])
            
            # Check if either side is eliminated or doesn't exist
            if not attacker or not defender or attacker.population == 0 or defender.population == 0:
                # Clean up war flags for all participants
                if attacker and attacker.population > 0:
                    attacker.is_at_war = False
                if defender and defender.population > 0:
                    defender.is_at_war = False
                
                # Reset war flags for allies
                for ally_id in war.get("attacker_allies", []):
                    if ally_id in nations_dict and nations_dict[ally_id].population > 0:
                        nations_dict[ally_id].is_at_war = False
                for ally_id in war.get("defender_allies", []):
                    if ally_id in nations_dict and nations_dict[ally_id].population > 0:
                        nations_dict[ally_id].is_at_war = False
                
                self.active_wars.remove(war)
                continue
            
            # Combat resolution using modified Lanchester equations
            result = self._resolve_combat(attacker, defender, war)
            
            if result:
                event_msg = self._apply_war_outcome(attacker, defender, war, result, nations)
                events.append(event_msg)
                self.active_wars.remove(war)
                self.war_history.append(war)
        
        return events
    
    def _resolve_combat(self, attacker: Nation, defender: Nation, war: Dict) -> Optional[str]:
        """
        Resolve combat using Lanchester square law with modifiers.
        Returns: "attacker_victory", "defender_victory", "stalemate", or None if ongoing.
        """
        # Calculate distance for supply lines
        # Simplified: Use Euclidean distance between capitals/centroids
        # We need access to HexGrid or World, but WarSystem doesn't have it directly.
        # We'll estimate based on trade route existence or just random variation for now,
        # OR we can pass distance in 'war' dict if we calculated it at start.
        # Let's assume 'war' dict has 'distance' key if we add it in initiate_war.
        distance = war.get("distance", 10) # Default short distance
        
        # Force strengths with supply penalty
        attacker_strength = self._calculate_combat_strength(attacker, is_attacker=True, distance=distance)
        defender_strength = self._calculate_combat_strength(defender, is_attacker=False, distance=0)
        
        # Technology multiplier
        tech_ratio = (attacker.technology + 1) / (defender.technology + 1)
        attacker_strength *= tech_ratio
        
        # Supply and logistics (GDP proxy)
        logistics_ratio = (attacker.gdp / max(1, defender.gdp)) ** 0.3
        attacker_strength *= logistics_ratio
        
        # War exhaustion reduces effectiveness
        attacker_strength *= (1 - attacker.war_exhaustion / 200)
        defender_strength *= (1 - defender.war_exhaustion / 200)
        
        # Home advantage for defender
        defender_strength *= 1.3
        
        # Nuclear weapons
        if attacker.military_power["nuclear"] > 10 and random.random() < 0.05:
            return self._nuclear_exchange(attacker, defender, war)
        
        # Apply casualties (Lanchester square law)
        attacker_casualties = defender_strength ** 2 * war["intensity"] * 0.01
        defender_casualties = attacker_strength ** 2 * war["intensity"] * 0.01
        
        attacker.population -= attacker_casualties
        defender.population -= defender_casualties
        
        # Economic damage
        attacker.gdp *= random.uniform(0.95, 0.98)
        defender.gdp *= random.uniform(0.90, 0.95)
        
        # War exhaustion increases
        # Democracies suffer more exhaustion from casualties
        exhaustion_base = random.uniform(2, 5)
        
        att_exhaustion = exhaustion_base * (1.5 if attacker.government_type == "Democracy" else 1.0)
        def_exhaustion = exhaustion_base * (1.2 if defender.government_type == "Democracy" else 0.8) # Defenders fight harder
        
        attacker.war_exhaustion += att_exhaustion
        defender.war_exhaustion += def_exhaustion
        
        # Morale decay (simulated by reducing effectiveness next turn via exhaustion)
        # We could add explicit 'morale' attribute to Nation, but exhaustion serves similar purpose inverse.
        pass
        
        # Check for resolution
        if war["duration"] < 3:
            return None  # Minimum war duration
            
        if war["duration"] > 12 or attacker.war_exhaustion > 80 or defender.war_exhaustion > 80:
            # Prolonged war or exhaustion leads to resolution
            if attacker_strength > defender_strength * 1.5:
                return "attacker_victory"
            elif defender_strength > attacker_strength * 1.5:
                return "defender_victory"
            else:
                return "stalemate"
        
        return None  # War continues
    
    def _calculate_combat_strength(self, nation: Nation, is_attacker: bool, distance: float = 0) -> float:
        """Calculate nation's effective military strength."""
        # Weighted average of military branches
        if is_attacker:
            # Attackers need projection capability (navy, air)
            strength = (nation.military_power["army"] * 0.3 +
                       nation.military_power["navy"] * 0.4 +
                       nation.military_power["air"] * 0.3)
            
            # Supply line penalty
            # Strength decays with distance: 10% per 10 tiles
            penalty = max(0.0, min(0.8, distance / 100.0))
            strength *= (1 - penalty)
            
        else:
            # Defenders rely more on army
            strength = (nation.military_power["army"] * 0.5 +
                       nation.military_power["navy"] * 0.25 +
                       nation.military_power["air"] * 0.25)
        
        # Population factor (manpower)
        # Ensure population is positive for log10
        safe_pop = max(1.0, nation.population)
        strength *= (1 + np.log10(safe_pop / 1e6) / 10)
        
        return strength
    
    def _nuclear_exchange(self, attacker: Nation, defender: Nation, war: Dict) -> str:
        """Handle nuclear weapons use."""
        # Both sides may retaliate
        attacker_nukes = int(attacker.military_power["nuclear"] / 10)
        defender_nukes = int(defender.military_power["nuclear"] / 10)
        
        self.nuclear_detonations += attacker_nukes + defender_nukes
        
        # Catastrophic damage
        attacker.population *= random.uniform(0.3, 0.5)
        defender.population *= random.uniform(0.2, 0.4)
        
        attacker.gdp *= random.uniform(0.2, 0.4)
        defender.gdp *= random.uniform(0.1, 0.3)
        
        attacker.stability = 10
        defender.stability = 10
        
        # Environmental damage
        war["nuclear_winter"] = True
        
        return "nuclear_exchange"
    
    def _apply_war_outcome(self, attacker: Nation, defender: Nation, 
                          war: Dict, result: str, nations: List[Nation]) -> str:
        """Apply war outcome and generate event message."""
        # Reset war flags for main combatants
        attacker.is_at_war = False
        defender.is_at_war = False
        
        # Reset war flags for allied nations
        nations_dict = {n.id: n for n in nations}
        for ally_id in war.get("attacker_allies", []):
            if ally_id in nations_dict and nations_dict[ally_id].population > 0:
                nations_dict[ally_id].is_at_war = False
        for ally_id in war.get("defender_allies", []):
            if ally_id in nations_dict and nations_dict[ally_id].population > 0:
                nations_dict[ally_id].is_at_war = False
        
        if result == "attacker_victory":
            # Annexation or regime change
            if random.random() < 0.3:
                # Annexation
                attacker.population += defender.population * 0.7
                attacker.gdp += defender.gdp * 0.5
                for resource in defender.resources:
                    attacker.resources[resource] = attacker.resources.get(resource, 0) + defender.resources[resource]
                
                defender.population = 0  # Nation destroyed
                return f"WAR END: {attacker.name} annexes {defender.name} after {war['duration']} months"
            else:
                # Regime change
                defender.government_type = attacker.government_type
                defender.ideology = attacker.ideology + random.gauss(0, 20)
                defender.stability = 30
                attacker.colonial_subjects.add(defender.id)
                
                # Reparations
                reparations = defender.gdp * 0.1
                defender.gdp -= reparations
                attacker.gdp += reparations * 0.7 # 30% friction
                
                return f"WAR END: {attacker.name} victory over {defender.name}, regime change imposed"
        
        elif result == "defender_victory":
            # Defender repels invasion
            attacker.stability -= 20
            attacker.war_exhaustion = 60
            
            # Reparations
            reparations = attacker.gdp * 0.1
            attacker.gdp -= reparations
            defender.gdp += reparations * 0.7
            
            return f"WAR END: {defender.name} successfully defends against {attacker.name}"
        
        elif result == "nuclear_exchange":
            return f"NUCLEAR WAR: {attacker.name} and {defender.name} exchange nuclear weapons! ({self.nuclear_detonations} total detonations)"
        
        else:  # Stalemate
            # Armistice
            attacker.war_exhaustion = 50
            defender.war_exhaustion = 50
            return f"WAR END: {attacker.name} and {defender.name} reach armistice after {war['duration']} months"
    
    def check_nuclear_winter(self) -> bool:
        """Check if nuclear winter conditions are met."""
        return self.nuclear_detonations >= 3
    
    def apply_nuclear_winter(self, nations: List[Nation]) -> str:
        """Apply global nuclear winter effects."""
        for nation in nations:
            if nation.population == 0:
                continue
            
            # Crop failures and famine
            nation.population *= random.uniform(0.5, 0.7)
            nation.gdp *= random.uniform(0.3, 0.5)
            nation.health -= 40
            nation.stability -= 30
            
            # Resource depletion (Permanent)
            if "farmland" in nation.resources:
                # Apply to both current and initial to ensure persistence across extraction resets
                nation.resources["farmland"] *= 0.3
                if "farmland" in nation.resources_initial:
                    nation.resources_initial["farmland"] *= 0.3
        
        return f"NUCLEAR WINTER: Global cooling and famine! {self.nuclear_detonations} warheads detonated"