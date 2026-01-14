from enum import Enum, auto
from typing import List, Dict, Set, Optional
import random
from dataclasses import dataclass, field

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
