from enum import Enum, auto
from typing import List, Dict, Set, Optional, Tuple
import random
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Forward reference for type hinting
# from nation import Nation # Avoid circular import, use string forward ref or 'object'

class AllianceType(Enum):
    DEFENSE_PACT = auto()    # NATO-style: Attack on one is attack on all
    TRADE_BLOC = auto()      # EU-style: Reduced trade friction
    NON_AGGRESSION = auto()  # Molotov-Ribbentrop: Won't attack each other

@dataclass
class Alliance:
    id: int
    name: str
    type: AllianceType
    members: Set[int] = field(default_factory=set)
    leader_id: Optional[int] = None
    cohesion: float = 100.0 # 0-100, affects likelihood of honoring obligations

class UnitedNations:
    """
    Manages global diplomacy, resolutions, and the Security Council.
    Replaces InternationalInstitutions.
    """
    def __init__(self, config):
        self.config = config
        self.security_council: Set[int] = set() # Permanent members (Veto power)
        self.members: Set[int] = set()
        self.resolutions_passed = 0
        self.resolutions_vetoed = 0
        self.sanctions: Dict[int, Set[int]] = {} # target_id -> set of sanctioning nation_ids
        self.peacekeepers_active: bool = False
        
    def calculate_alliance_value(self, nation_a: 'Nation', nation_b: 'Nation', economy) -> float:
        """Calculate strategic value of alliance A→B (why A would defend B)."""
        value = 0.0
        
        # 1. Economic Integration (trade dependency)
        trade_volume = economy.trade_volumes.get((nation_a.id, nation_b.id), 0)
        if nation_a.gdp > 0:
            value += (trade_volume / nation_a.gdp) * 50  # Up to +50 if 100% trade dependent
        
        # 2. Strategic Resources (e.g., Taiwan semiconductors = rare_earth)
        if "rare_earth" in nation_b.resources:
            # High-tech resources are strategically critical
            if nation_b.resources["rare_earth"] > 30 and nation_a.technology > 70:
                value += 40  # Tech-dependent nations value rare earth sources
        
        # 3. FDI Exposure (protecting investments)
        fdi_exposure = nation_a.fdi_positions.get(nation_b.id, 0)
        if nation_a.gdp > 0:
            value += (fdi_exposure / nation_a.gdp) * 30
        
        # 4. Ideological Alignment
        ideology_diff = abs(nation_a.ideology - nation_b.ideology)
        value += max(0, 30 - ideology_diff / 3)  # Up to +30 for similar ideology
        
        return value
    
    def should_defend_ally(self, defender: 'Nation', attacker: 'Nation', ally: 'Nation', economy) -> bool:
        """Decide if ally should join defensive war (cost-benefit analysis)."""
        # Calculate cost-benefit
        alliance_value = self.calculate_alliance_value(ally, defender, economy)
        
        # Risk assessment - can we actually help?
        ally_power = ally.get_total_military_power()
        attacker_power = attacker.get_total_military_power()
        military_ratio = ally_power / max(1, attacker_power)
        
        # Won't fight hopeless wars
        if military_ratio < 0.3:
            return False
        
        # High value targets worth risking
        if alliance_value > 60:
            return random.random() < 0.8  # 80% chance to defend critical ally
        elif alliance_value > 40:
            return random.random() < 0.5  # 50% chance
        elif alliance_value > 20:
            return random.random() < 0.2  # 20% chance
        else:
            return False  # Not worth it
    
    def check_alliance_interventions(self, active_wars: List[Dict], nations: List['Nation'], economy) -> List[Tuple]:
        """Check if allies should join ongoing wars."""
        interventions = []
        nations_dict = {n.id: n for n in nations}
        
        for war in active_wars:
            defender_id = war.get("defender_id")
            attacker_id = war.get("attacker_id")
            
            defender = nations_dict.get(defender_id)
            attacker = nations_dict.get(attacker_id)
            
            if not defender or not attacker:
                continue
            
            # Check defender's allies
            for ally_id in defender.alliances:
                ally = nations_dict.get(ally_id)
                if not ally or ally.is_at_war or ally.population == 0:
                    continue
                
                # Already in war?
                if ally_id in war.get("defender_allies", []):
                    continue
                
                # Should this ally intervene?
                if self.should_defend_ally(defender, attacker, ally, economy):
                    interventions.append((ally_id, war, "defender"))
                    logger.warning(f"ALLIANCE ACTIVATED: {ally.name} joins war to defend {defender.name}")
            
            # Check attacker's counter-alliances (less common)
            for ally_id in attacker.alliances:
                ally = nations_dict.get(ally_id)
                if not ally or ally.is_at_war or ally.population == 0:
                    continue
                
                if ally_id in war.get("attacker_allies", []):
                    continue
                
                # Counter-intervention (less likely)
                alliance_value = self.calculate_alliance_value(ally, attacker, economy)
                if alliance_value > 50:
                    if random.random() < 0.4:  # Less likely than defensive intervention
                        interventions.append((ally_id, war, "attacker"))
                        logger.info(f"ALLIANCE ACTIVATED: {ally.name} joins {attacker.name}'s offensive")
        
        return interventions
    
    def update_security_council(self, nations: List['Nation']):
        """Update security council based on GDP/Power (Dynamic UNSC)."""
        # In this sim, UNSC is dynamic based on power, not fixed 1945 victors
        living_nations = [n for n in nations if n.population > 0]
        living_nations.sort(key=lambda n: n.gdp + n.get_total_military_power() * 1e9, reverse=True)
        
        # Top 5 are permanent members
        self.security_council = {n.id for n in living_nations[:5]}
        
    def propose_resolution(self, proposer: 'Nation', resolution_type: str, target: 'Nation', nations: List['Nation']) -> bool:
        """
        Propose and vote on a UN resolution.
        Types: "sanctions", "peacekeeping", "condemnation", "aid"
        """
        nations_dict = {n.id: n for n in nations}
        
        # 1. Security Council Vote (Veto Check)
        for member_id in self.security_council:
            if member_id not in nations_dict: continue
            member = nations_dict[member_id]
            
            # Veto Logic
            veto = False
            if resolution_type in ["sanctions", "condemnation"]:
                # Veto if target is ally or self
                if target.id == member.id or target.id in member.alliances:
                    veto = True
                # Veto if ideologically aligned (Autocracies protect Autocracies)
                elif abs(member.ideology - target.ideology) < 20:
                    veto = True
            
            if veto:
                # 90% chance to actually use veto if conditions met
                if random.random() < 0.9:
                    self.resolutions_vetoed += 1
                    return False
                    
        # 2. General Assembly Vote
        # Simple majority needed
        votes_for = 0
        votes_against = 0
        abstentions = 0
        
        for nation in nations:
            if nation.population == 0: continue
            
            vote = self._cast_vote(nation, resolution_type, target, proposer)
            if vote == "yes":
                votes_for += 1
            elif vote == "no":
                votes_against += 1
            else:
                abstentions += 1
                
        passed = votes_for > (votes_for + votes_against) / 2
        
        if passed:
            self.resolutions_passed += 1
            self._enforce_resolution(resolution_type, target, nations)
            
        return passed

    def _cast_vote(self, nation: 'Nation', res_type: str, target: 'Nation', proposer: 'Nation') -> str:
        """Determine how a nation votes."""
        # Base alignment
        score = 0.0
        
        # Relations with target
        if target.id in nation.alliances: score -= 50
        if target.id == nation.id: score -= 100
        
        # Relations with proposer
        if proposer.id in nation.alliances: score += 20
        
        # Ideology
        ideology_diff = abs(nation.ideology - target.ideology)
        if res_type in ["sanctions", "condemnation"]:
            if ideology_diff > 50: score += 30 # Punish opposing ideology
            else: score -= 20 # Protect similar ideology
            
        # Random noise / National Interest
        score += random.gauss(0, 10)
        
        if score > 10: return "yes"
        if score < -10: return "no"
        return "abstain"

    def _enforce_resolution(self, res_type: str, target: 'Nation', nations: List['Nation']):
        """Apply effects of passed resolution."""
        if res_type == "sanctions":
            # Global sanctions (except allies)
            for n in nations:
                if n.id != target.id and target.id not in n.alliances:
                    n.sanctions_active.add(target.id)
                    target.sanctions_from.add(n.id)
            target.gdp *= 0.95 # Immediate shock
            
        elif res_type == "aid":
            # Transfer wealth
            amount = 1e9
            contributors = [n for n in nations if n.gdp > 1e11 and n.id != target.id]
            if contributors:
                share = amount / len(contributors)
                for c in contributors:
                    c.gdp -= share
                target.gdp += amount
                target.stability += 5

    def arbitrate_trade_dispute(self, nation_a: 'Nation', nation_b: 'Nation') -> str:
        """
        WTO-like arbitration of trade disputes.
        Returns winning party name or "settled".
        """
        # Favor more stable, developed nation
        score_a = nation_a.stability + nation_a.technology
        score_b = nation_b.stability + nation_b.technology
        
        if abs(score_a - score_b) < 20:
            return "settled"
        
        return nation_a.name if score_a > score_b else nation_b.name
