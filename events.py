"""
Random events system with realistic probabilities.
Includes elections, coups, disasters, pandemics, and institutional changes.
"""

from typing import List, Dict, Optional
import random
import numpy as np

from nation import Nation
from config import SimulationConfig, GOVERNMENT_TYPES


class EventSystem:
    """Manages stochastic events affecting nations."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.active_pandemics: List[Dict] = []
        self.event_log: List[Dict] = []
        
        # Decolonization wave tracking
        self.recent_independence_events: List[Tuple[int, int, int]] = []  # (step, colonizer_id, colony_id)
        
        # Oil embargo tracking
        self.active_embargoes: List[Dict] = []  # {start_step, initiator_id, duration, severity}
    
    def process_events(self, nations: List[Nation], economy, step: int, hex_grid=None) -> List[str]:
        """Process all random events for the turn."""
        self.events = []
        
        # Check for new events
        self._check_new_events(nations, step)
        
        # Update ongoing events
        self._update_pandemics(nations, economy, self.events, hex_grid)
        
        return self.events
    
    def check_oil_embargo(self, nations: List[Nation], wars: List[Dict], step: int) -> Optional[str]:
        """Check if active wars trigger oil embargoes (supply shocks)."""
        nations_dict = {n.id: n for n in nations}
        
        for war in wars:
            attacker_id = war.get("attacker_id")
            defender_id = war.get("defender_id")
            
            attacker = nations_dict.get(attacker_id)
            defender = nations_dict.get(defender_id)
            
            if not attacker or not defender:
                continue
            
            # Check if either side is a major oil producer
            attacker_oil = attacker.resources.get("oil", 0)
            defender_oil = defender.resources.get("oil", 0)
            
            # Major oil producer = oil > 50
            if attacker_oil > 50 or defender_oil > 50:
                # 30% chance per step that embargo triggers
                if random.random() < 0.3:
                    initiator = defender if defender_oil > 50 else attacker
                    
                    # Check if embargo already active from this initiator
                    already_active = any(e["initiator_id"] == initiator.id 
                                        for e in self.active_embargoes)
                    
                    if not already_active:
                        embargo = {
                            "start_step": step,
                            "initiator_id": initiator.id,
                            "initiator_name": initiator.name,
                            "duration": random.randint(6, 12),  # 6-12 months
                            "severity": random.uniform(0.3, 0.5)  # 30-50% impact
                        }
                        self.active_embargoes.append(embargo)
                        logger.warning(f"OIL EMBARGO: {initiator.name} restricts oil exports (severity {embargo['severity']:.0%})")
                        return f"OIL EMBARGO: {initiator.name} cuts oil supply to hostile nations"
        
        return None
    
    def _check_new_events(self, nations: List[Nation], step: int):
        """Checks for and triggers new, non-pandemic events."""
        for nation in nations:
            if nation.population <= 0:
                continue
            
            # Elections (democracies only)
            if nation.government_type == "Democracy":
                if step - nation.last_election >= 4 or random.random() < self.config.event_election_prob:
                    event = self._election(nation, step)
                    if event:
                        self.events.append(event)
            
            # Coups (more likely in unstable autocracies)
            if nation.stability < self.config.rebellion_instability_threshold:
                coup_prob = self.config.event_coup_base_prob * (1 + (50 - nation.stability) / 50)
                if random.random() < coup_prob:
                    event = self._coup(nation)
                    if event:
                        self.events.append(event)
            
            # Corruption scandals
            if random.random() < 0.02 * (100 - nation.stability) / 100:
                event = self._corruption_scandal(nation)
                self.events.append(event)
            
            # Natural disasters
            if random.random() < self.config.event_disaster_prob:
                event = self._natural_disaster(nation)
                self.events.append(event)
            
            # Tech breakthroughs
            if nation.technology > 60 and random.random() < 0.02:
                event = self._tech_breakthrough(nation)
                self.events.append(event)
            
            # Debt defaults
            if nation.debt_to_gdp > 1.0 and random.random() < 0.05:
                event = self._debt_default(nation)
                self.events.append(event)
        
        # Global pandemic (rare)
        if not self.active_pandemics and random.random() < self.config.event_pandemic_prob:
            pandemic = self._spawn_pandemic(nations)
            if pandemic:
                self.events.append(f"GLOBAL PANDEMIC: {pandemic['name']} emerges (R0={pandemic['r0']:.1f}, lethality={pandemic['lethality']:.1%})")
    
    def _election(self, nation: Nation, step: int) -> Optional[str]:
        """Democratic election with potential ideology/policy shifts."""
        nation.last_election = step
        
        # Update baseline for next election regardless of outcome
        # We do this first so we compare against the OLD baseline this time, 
        # but save the NEW baseline for next time.
        # Wait, we need to compare first.
        
        # Economic performance affects incumbent
        prev_gdp = getattr(nation, "_prev_gdp_election", nation.gdp)
        gdp_growth = (nation.gdp / max(1, prev_gdp)) - 1
        
        # Update baseline for NEXT election
        nation._prev_gdp_election = nation.gdp
        
        # Determine if government changes
        change_prob = 0.5 - gdp_growth * 2  # Good economy helps incumbent
        change_prob += (100 - nation.stability) / 200  # Instability hurts incumbent
        
        if random.random() < change_prob:
            # Ideology shift
            old_ideology = nation.ideology
            nation.ideology += random.gauss(0, 15)
            nation.ideology = max(-100, min(100, nation.ideology))
            
            # Potential government type change
            if abs(nation.ideology - old_ideology) > 30:
                if random.random() < 0.3:
                    old_gov = nation.government_type
                    if nation.ideology > 50:
                        nation.government_type = random.choice(["Democracy", "Autocracy"])
                    else:
                        nation.government_type = random.choice(["Democracy", "Technocracy"])
                    
                    return f"ELECTION: {nation.name} shifts from {old_gov} to {nation.government_type}"
            
            return f"ELECTION: {nation.name} elects new government (ideology shift to {nation.ideology:.0f})"
        
        return None
    
    def _coup(self, nation: Nation) -> Optional[str]:
        """Military coup or revolution."""
        if nation.government_type == "Anarchy":
            return None  # Already anarchic
        
        old_gov = nation.government_type
        
        # Coups tend toward autocracy
        if random.random() < 0.7:
            nation.government_type = "Autocracy"
        else:
            nation.government_type = random.choice(["Anarchy", "Theocracy"])
        
        # Coup damages stability and economy
        nation.stability -= random.uniform(20, 40)
        nation.gdp *= random.uniform(0.85, 0.95)
        nation.military_power["army"] *= 0.9  # Some military losses
        
        # Ideology shift
        nation.ideology += random.gauss(0, 30)
        nation.ideology = max(-100, min(100, nation.ideology))
        
        return f"COUP: {nation.name} government overthrown! {old_gov} → {nation.government_type}"
    
    def _corruption_scandal(self, nation: Nation) -> str:
        """Political corruption reduces stability and GDP."""
        gdp_loss = random.uniform(0.02, 0.05)
        stability_loss = random.uniform(5, 15)
        
        nation.gdp *= (1 - gdp_loss)
        nation.stability -= stability_loss
        
        return f"SCANDAL: Corruption exposed in {nation.name} (GDP -{gdp_loss:.1%}, stability -{stability_loss:.0f})"
    
    def _natural_disaster(self, nation: Nation) -> str:
        """Natural disaster damages economy and population."""
        disaster_types = ["earthquake", "hurricane", "flood", "drought", "tsunami"]
        disaster = random.choice(disaster_types)
        
        # Impact based on preparedness (tech, wealth)
        severity = random.uniform(0.5, 1.0) * (1 - nation.technology / 200)
        
        pop_loss = severity * 0.02
        gdp_loss = severity * 0.05
        
        nation.population *= (1 - pop_loss)
        nation.gdp *= (1 - gdp_loss)
        nation.stability -= severity * 10
        
        return f"DISASTER: {disaster.capitalize()} strikes {nation.name} ({pop_loss:.1%} casualties, ${gdp_loss*nation.gdp/1e9:.1f}B damage)"
    
    def _tech_breakthrough(self, nation: Nation) -> str:
        """Major technological breakthrough."""
        breakthrough_types = {
            "AI": 5, "Fusion": 4, "Quantum": 3, "Biotech": 4, "Nanotech": 3
        }
        tech_type = random.choice(list(breakthrough_types.keys()))
        tech_gain = breakthrough_types[tech_type]
        
        nation.technology = min(100, nation.technology + tech_gain)
        nation.gdp *= random.uniform(1.02, 1.05)  # Economic boost
        
        return f"BREAKTHROUGH: {nation.name} achieves {tech_type} breakthrough (+{tech_gain} tech)"
    
    def _debt_default(self, nation: Nation) -> str:
        """Sovereign debt default."""
        haircut = random.uniform(0.3, 0.5)
        nation.debt_to_gdp *= (1 - haircut)
        nation.gdp *= 0.85  # Economic crisis
        nation.stability -= 25
        nation.currency.exchange_rate *= 0.6  # Currency collapse
        
        return f"DEFAULT: {nation.name} defaults on debt ({haircut:.0%} haircut, currency -40%)"
    
    def _spawn_pandemic(self, nations: List[Nation]) -> Dict:
        """Spawn new global pandemic."""
        pandemic = {
            "name": f"Virus-{random.randint(1000, 9999)}",
            "r0": max(0.5, random.gauss(self.config.pandemic_r0_mean, self.config.pandemic_r0_std)),
            "lethality": max(0.001, random.gauss(self.config.pandemic_lethality_mean, 
                                                 self.config.pandemic_lethality_std)),
            "vaccine_time": int(random.gauss(self.config.pandemic_vaccine_time_mean, 3)),
            "infected_nations": set(),
            "time_active": 0
        }
        
        # Patient zero in random nation
        living_nations = [n for n in nations if n.population > 0]
        if not living_nations:
            return None
            
        origin = random.choice(living_nations)
        pandemic["infected_nations"].add(origin.id)
        origin.pandemic_active = True
        
        self.active_pandemics.append(pandemic)
        return pandemic
    
    def _update_pandemics(self, nations: List[Nation], economy, events: List[str], hex_grid=None):
        """Update pandemic spread and effects."""
        nations_dict = {n.id: n for n in nations}
        
        for pandemic in self.active_pandemics[:]:
            pandemic["time_active"] += 1
            
            # Spread to connected nations
            new_infections = []
            for nation_id in pandemic["infected_nations"]:
                if nation_id not in nations_dict:
                    continue
                nation = nations_dict[nation_id]
                
                # Healthcare Collapse Check
                # If infected % > capacity, mortality spikes
                # Simplified: If lethality * infected > health/1000
                if pandemic["lethality"] > nation.health / 2000.0:
                     pandemic["lethality"] *= 1.1 # Worsens as system collapses
                
                # Population impact
                deaths = nation.population * pandemic["lethality"] * random.uniform(0.5, 1.5)
                nation.population -= deaths
                
                # Quarantine decision
                # If pandemic is severe, nations may quarantine
                quarantine_strength = 0.0
                if pandemic["lethality"] > 0.05 or len(pandemic["infected_nations"]) > len(nations) * 0.3:
                    # Autocracies quarantine harder
                    if nation.government_type in ["Autocracy", "Technocracy"]:
                        quarantine_strength = 0.8
                    else:
                        quarantine_strength = 0.5
                
                # Economic impact (worsened by quarantine)
                # Sector differentiation: Services hit harder than Ag/Industry
                # We don't have explicit sectors, but we can model it as general GDP hit
                base_impact = 0.98
                if quarantine_strength > 0.5:
                    base_impact = 0.90 # Severe lockdown
                
                gdp_impact = base_impact * random.uniform(0.98, 1.02)
                nation.gdp *= gdp_impact
                
                # Spread via trade routes
                potential_targets = []
                if economy:
                    potential_targets = economy.get_nation_trade_partners(nation.id)
                
                # Fallback if no trade partners or economy not passed
                if not potential_targets:
                    potential_targets = list(nation.alliances)
                    potential_targets.extend([n.id for n in random.sample(nations, min(3, len(nations)))])
                
                spread_attempts = int(pandemic["r0"] * (1 - quarantine_strength))
                
                for target_id in potential_targets:
                    if target_id not in nations_dict: continue
                    target = nations_dict[target_id]
                    
                    if target.population > 0 and target.id not in pandemic["infected_nations"]:
                        # Target quarantine logic (pre-emptive)
                        target_quarantine = 0.0
                        if pandemic["lethality"] > 0.05 or len(pandemic["infected_nations"]) > len(nations) * 0.2:
                             if target.government_type in ["Autocracy", "Technocracy"]:
                                 target_quarantine = 0.8
                             else:
                                 target_quarantine = 0.5
                        
                        # Distance Factor
                        dist_factor = 1.0
                        if hex_grid and nation.territory_tiles and target.territory_tiles:
                             # Use centroid distance (first tile as proxy)
                             c1 = nation.territory_tiles[0]
                             c2 = target.territory_tiles[0]
                             dist = hex_grid.distance(c1[0], c1[1], c2[0], c2[1])
                             # Decay spread probability with distance
                             dist_factor = max(0.1, 1.0 - (dist / 50.0))
                        
                        # Air Travel Factor (GDP proxy)
                        # Higher GDP nations likely have more international travel
                        air_factor = 1.0
                        if nation.gdp > 1e12 and target.gdp > 1e12: # Both nations are wealthy
                            air_factor = 1.5
                        elif nation.gdp > 5e11 or target.gdp > 5e11: # One is wealthy
                            air_factor = 1.2
                        
                        # Spread probability based on health system and quarantine
                        # Combined quarantine effect (source + target)
                        spread_prob = 0.3 * (1 - target.health / 200) * (1 - quarantine_strength) * (1 - target_quarantine)
                        spread_prob *= dist_factor * air_factor
                        
                        if random.random() < spread_prob:
                            new_infections.append(target.id)
                            target.pandemic_active = True
            
            pandemic["infected_nations"].update(new_infections)
            
            # Vaccine development
            if pandemic["time_active"] >= pandemic["vaccine_time"]:
                # End pandemic
                for nation_id in pandemic["infected_nations"]:
                    if nation_id in nations_dict:
                        nations_dict[nation_id].pandemic_active = False
                
                events.append(f"PANDEMIC END: {pandemic['name']} vaccine developed after {pandemic['time_active']} months")
                self.active_pandemics.remove(pandemic)