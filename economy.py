"""
Global economic system with trade, FDI, and institutional mechanics.
Implements multilateral trade networks, capital flows, and currency markets.
"""

from __future__ import annotations
from typing import List, Dict, Tuple, TYPE_CHECKING
import random
import numpy as np

if TYPE_CHECKING:
    # import only for type-checking to avoid circular imports at runtime
    from nation import Nation

from config import SimulationConfig


class GlobalEconomy:
    """Manages international trade, FDI, and currency markets."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.trade_agreements: List[Tuple[int, int]] = []
        self.trade_volumes: Dict[Tuple[int, int], float] = {}
        self.global_reserve_currency = "GRC"  # Global Reserve Currency
    
    def calculate_comparative_advantage(self, nation_a: 'Nation', 
                                       nation_b: 'Nation') -> float:
        """
        Calculate trade benefit using Ricardian comparative advantage.
        Returns multiplier based on complementary resources and tech differences.
        """
        # Resource complementarity
        resource_comp = 0
        for resource in ["oil", "rare_earth", "farmland"]:
            diff = abs(nation_a.resources.get(resource, 0) - 
                      nation_b.resources.get(resource, 0))
            resource_comp += diff
        
        # Technology spillover benefit
        tech_diff = abs(nation_a.technology - nation_b.technology)
        tech_benefit = min(tech_diff / 100, 0.2)  # Max 20% benefit
        
        # Ideological friction reduces trade
        ideology_penalty = abs(nation_a.ideology - nation_b.ideology) / 1000
        
        advantage = (resource_comp * 0.01 + tech_benefit - ideology_penalty)
        return max(0, advantage)
    
    def update_trade_network(self, nations: List[Nation], hex_grid=None):
        """
        Recalculate trade volumes based on gravity model and comparative advantage.
        Uses HexGrid for distance if provided.
        """
        self.trade_agreements = []
        self.trade_volumes = {}
        
        for i, nation_a in enumerate(nations):
            if not nation_a.population > 0:
                continue
            
            for j, nation_b in enumerate(nations[i+1:], start=i+1):
                if not nation_b.population > 0:
                    continue
                
                # Skip if sanctioned
                if nation_a.id in nation_b.sanctions_from or nation_b.id in nation_a.sanctions_from:
                    continue
                
                # Calculate distance using territory centroids
                # If nations have no territory (shouldn't happen if pop > 0), use default
                if not nation_a.territory_tiles or not nation_b.territory_tiles:
                    distance = 50.0
                else:
                    # Calculate centroids
                    cx_a = sum(t[0] for t in nation_a.territory_tiles) / len(nation_a.territory_tiles)
                    cy_a = sum(t[1] for t in nation_a.territory_tiles) / len(nation_a.territory_tiles)
                    
                    cx_b = sum(t[0] for t in nation_b.territory_tiles) / len(nation_b.territory_tiles)
                    cy_b = sum(t[1] for t in nation_b.territory_tiles) / len(nation_b.territory_tiles)
                    
                    # Toroidal distance
                    if hex_grid:
                        # Use HexGrid distance (approximate centroid)
                        distance = hex_grid.distance(int(cx_a), int(cy_a), int(cx_b), int(cy_b))
                    else:
                        w, h = self.config.world_width, self.config.world_height
                        dx = min(abs(cx_a - cx_b), w - abs(cx_a - cx_b))
                        dy = min(abs(cy_a - cy_b), h - abs(cy_a - cy_b))
                        distance = (dx**2 + dy**2) ** 0.5
                    
                    distance = max(1.0, distance) # Avoid zero division
                
                # Gravity model
                gravity = (nation_a.gdp * nation_b.gdp) / (distance ** 2)
                
                # Geography Modifiers
                geo_penalty = 1.0
                # Landlocked penalty
                if not nation_a.is_coastal: geo_penalty *= 0.5
                if not nation_b.is_coastal: geo_penalty *= 0.5
                
                # Naval power requirement for long-distance trade
                if distance > 30:
                    if nation_a.military_power.get("navy", 0) < 10: geo_penalty *= 0.8
                    if nation_b.military_power.get("navy", 0) < 10: geo_penalty *= 0.8
                
                # Comparative advantage boost
                advantage = self.calculate_comparative_advantage(nation_a, nation_b)
                
                # Alliance bonus
                alliance_bonus = 1.2 if nation_a.id in nation_b.alliances else 1.0
                
                # Calculate trade volume
                trade_volume = gravity * (1 + advantage) * alliance_bonus * geo_penalty * 1e-10
                
                if trade_volume > nation_a.gdp * 0.01:  # Meaningful trade threshold
                    self.trade_agreements.append((nation_a.id, nation_b.id))
                    self.trade_volumes[(nation_a.id, nation_b.id)] = trade_volume
                    
                    # Update trade balances (simplified)
                    balance_shift = random.uniform(-0.3, 0.3) * trade_volume
                    nation_a.trade_balance += balance_shift
                    nation_b.trade_balance -= balance_shift
    
    def calculate_global_trade_multiplier(self, nation: Nation) -> float:
        """
        Calculate nation's benefit from global trade integration.
        More trade partners = higher GDP boost (Ricardian gains).
        """
        trade_count = sum(1 for (a, b) in self.trade_agreements 
                         if nation.id in (a, b))
        
        base_boost = trade_count * self.config.trade_comparative_advantage_boost
        
        # Diminishing returns
        multiplier = 1.0 + base_boost * (1 - base_boost / 0.3)
        return min(1.5, multiplier)  # Max 50% boost from trade
    
    def process_fdi_flows(self, nations: List[Nation]):
        """
        Process Foreign Direct Investment with risk-adjusted returns.
        Includes Capital Flight mechanics during instability.
        """
        # 1. Capital Flight Phase
        nations_dict = {n.id: n for n in nations}
        for investor in nations:
            # Check existing positions for flight triggers
            for target_id in list(investor.fdi_positions.keys()):
                if target_id not in nations_dict:
                    continue
                target = nations_dict[target_id]
                
                # Flight triggers: Instability, War, or Capital Controls (implied)
                flight_triggered = False
                flight_severity = 0.0
                
                if target.stability < 40:
                    flight_triggered = True
                    flight_severity += 0.2
                if target.is_at_war:
                    flight_triggered = True
                    flight_severity += 0.3
                if target.population == 0:
                    # Total loss
                    del investor.fdi_positions[target_id]
                    continue
                    
                if flight_triggered:
                    # Calculate flight amount
                    current_position = investor.fdi_positions[target_id]
                    flight_amount = current_position * flight_severity
                    
                    # Execute flight
                    investor.fdi_positions[target_id] -= flight_amount
                    if investor.fdi_positions[target_id] < 1e6:
                        del investor.fdi_positions[target_id]
                        
                    # Economic Impact
                    # Repatriation: Investor reduces their foreign asset position (negative outflow)
                    investor.fdi_outflows -= flight_amount 
                    # Target loses foreign investment (negative inflow)
                    target.fdi_inflows -= flight_amount
                    
                    # Shock target economy
                    # Cap the shock to prevent negative GDP
                    shock_factor = min(0.5, (flight_amount / target.gdp) * 2.0)
                    target.gdp *= (1.0 - shock_factor) 
                    target.currency.exchange_rate *= 0.95 # Currency hit
                    target.stability -= 2 # Vicious cycle
                    
        # 2. New Investment Phase
        for investor in nations:
            if investor.gdp < 1e11:  # Only wealthy nations invest abroad
                continue
            
            # Determine FDI budget (% of GDP)
            fdi_budget = investor.gdp * random.uniform(0.01, 0.05)
            
            # Find attractive investment targets
            targets = []
            for target in nations:
                if target.id == investor.id or target.population == 0:
                    continue
                
                # Expected return = base return + growth potential - risk
                growth_potential = (100 - target.technology) / 100 * 0.05
                risk = (100 - target.stability) / 100 * self.config.fdi_risk_premium
                expected_return = self.config.fdi_return_rate + growth_potential - risk
                
                if expected_return > 0.02:  # Minimum acceptable return
                    targets.append((target, expected_return))
            
            # Allocate FDI to top targets
            if targets:
                targets.sort(key=lambda x: x[1], reverse=True)
                for target, _ in targets[:3]:  # Top 3 destinations
                    investment = fdi_budget / 3
                    
                    investor.fdi_outflows += investment
                    target.fdi_inflows += investment
                    
                    # Track Position
                    investor.fdi_positions[target.id] = investor.fdi_positions.get(target.id, 0.0) + investment
                    
                    # Technology transfer with FDI
                    tech_transfer = (investor.technology - target.technology) * self.config.tech_spillover_rate * 0.1
                    target.technology += max(0, tech_transfer)
                    
                    # Create economic dependency
                    investor.colonial_influence += 0.1
                    
                    # Check for colonial subject status based on total stock vs GDP
                    total_stock = sum(n.fdi_positions.get(target.id, 0) for n in nations)
                    if total_stock > target.gdp * 0.5:
                        # High dependency risk (simplified: if this investor is dominant)
                        if investor.fdi_positions[target.id] > total_stock * 0.5:
                            investor.colonial_subjects.add(target.id)

    def process_colonial_relations(self, nations: List[Nation]):
        """
        Handle economic extraction from colonies and independence movements.
        """
        for nation in nations:
            # 1. Pay tribute to colonizers
            # If nation is a subject of others (check all nations to find masters)
            # Optimization: Iterate masters instead
            if not nation.colonial_subjects:
                continue
                
            # Copy set to allow modification
            subjects = list(nation.colonial_subjects)
            for subject_id in subjects:
                subject = nations[subject_id]
                if subject.population == 0:
                    nation.colonial_subjects.discard(subject_id)
                    continue
                
                # Tribute: 2-5% of GDP
                tribute_rate = 0.03
                tribute = subject.gdp * tribute_rate
                
                # Unequal Exchange: Resource Drain
                # Colonizer gets resources at discount (simulated by extra GDP transfer)
                resource_drain = 0.0
                for res, amount in subject.resources.items():
                    if amount > 0:
                        drain = amount * 0.01 # 1% of resources extracted cheap
                        resource_drain += drain * 1e6 # Value approximation
                        subject.resources[res] -= drain
                
                total_transfer = tribute + resource_drain
                subject.gdp -= total_transfer
                nation.gdp += total_transfer
                
                # Infrastructure built for extraction (doesn't help subject much)
                # Colonizer invests but it goes to "extraction_infra" not general capital
                # Modeled as: Subject gets no capital stock boost from this "investment"
                pass
                
                # 2. Independence Check
                # Probability increases if:
                # - Subject has high tech AND high stability
                # - Colonizer is weak (low stability or GDP decline)
                # - Ideological difference
                
                # Require minimum stability for organized independence movement
                if subject.stability < 50:
                    continue  # Too unstable to organize
                
                tech_factor = (subject.technology / 100.0) ** 2  # Squared for stronger effect
                weakness_factor = (100 - nation.stability) / 100.0
                ideology_diff = abs(nation.ideology - subject.ideology) / 200.0
                
                # Base revolt probability
                revolt_prob = 0.05 * tech_factor * (1 + weakness_factor) * (1 + ideology_diff)
                
                # Anti-colonial coalition bonus
                # Check if other colonies exist and are also high-tech
                coalition_bonus = 0.0
                for other_subject_id in nation.colonial_subjects:
                    if other_subject_id != subject.id:
                        other_subject = nations_dict.get(other_subject_id)
                        if other_subject and other_subject.technology > 60:
                            coalition_bonus += 0.02  # Each potential ally adds 2%
                
                revolt_prob += min(0.1, coalition_bonus)  # Cap at 10% bonus
                
                if random.random() < revolt_prob:
                    # Independence War / Peaceful Separation
                    nation.colonial_subjects.discard(subject_id)
                    subject.stability += 15  # Increased from 10
                    subject.ideology -= (nation.ideology * 0.3)  # Move away from colonizer
                    nation.stability -= 10  # Increased from 5
                    
                    # Seize assets and nationalize
                    if subject.id in nation.fdi_positions:
                        seized = nation.fdi_positions[subject.id]
                        nation.fdi_positions[subject.id] = 0
                        nation.fdi_outflows -= seized  # Write off
                        # Subject gains assets (nationalization) -> capital stock boost
                        subject.capital_stock += seized
                    
                    # Form alliance with other recent independence movements
                    for other_subject_id in list(nation.colonial_subjects):
                        if other_subject_id != subject.id:
                            other_subject = nations_dict.get(other_subject_id)
                            if other_subject and other_subject.technology > 60:
                                # Anti-colonial coalition
                                subject.alliances.add(other_subject_id)
                                other_subject.alliances.add(subject.id)
                        
                    # Event logging would happen here if we had access to event queue
                    # For now, just the mechanic
    
    def update_exchange_rates(self, nations: List[Nation]):
        """Update currency exchange rates based on macroeconomic fundamentals."""
        # Calculate global average inflation
        avg_inflation = np.mean([n.inflation_rate for n in nations if n.population > 0])
        
        for nation in nations:
            if nation.population == 0:
                continue
            
            # Balance of payments
            bop = (nation.trade_balance + nation.fdi_inflows - nation.fdi_outflows) / nation.gdp
            
            # Inflation differential vs global average
            inflation_diff = nation.inflation_rate - avg_inflation
            
            nation.currency.update_exchange_rate(bop, inflation_diff, self.config)
    
    def simulate_debt_crisis(self, nation: Nation, nations: List[Nation]) -> bool:
        """
        Check for sovereign debt crisis and handle default.
        High debt + low growth + currency depreciation = crisis.
        """
        if nation.debt_to_gdp > 1.2:  # >120% debt-to-GDP
            gdp_growth = (nation.gdp / max(1, getattr(nation, "_prev_gdp_debt", nation.gdp))) - 1
            
            crisis_prob = (nation.debt_to_gdp - 1.0) * 0.3
            if gdp_growth < 0:
                crisis_prob += 0.2  # Recession amplifies risk
            
            if random.random() < crisis_prob:
                # Sovereign default
                nation.debt_to_gdp *= 0.6  # Haircut
                nation.gdp *= 0.9  # Economic contraction
                nation.stability -= 20
                nation.currency.exchange_rate *= 0.7  # Devaluation
                
                # Contagion
                partners = self.get_nation_trade_partners(nation.id)
                nations_dict = {n.id: n for n in nations}
                
                for pid in partners:
                    if pid in nations_dict:
                        partner = nations_dict[pid]
                        # Spread probability based on trade volume dependency
                        # Simplified: 30% chance
                        if random.random() < 0.3:
                            partner.currency.exchange_rate *= 0.9
                            partner.gdp *= 0.98
                            partner.stability -= 5
                            # Recursive contagion could happen next step
                
                return True
        
        # Speculative Attack Check (Interest Rate Parity)
        if self._check_speculative_attack(nation):
            nation.currency.exchange_rate *= 0.85
            nation.stability -= 10
            nation.crisis_active = True
            nation.crisis_duration = 0
            return True
            
        nation._prev_gdp_debt = nation.gdp
        return False

    def _check_speculative_attack(self, nation: Nation) -> bool:
        """
        Check for speculative attack based on Interest Rate Parity.
        If domestic rate < foreign rate + expected depreciation, attack occurs.
        """
        if nation.currency.regime == "pegged":
            return False # Pegged currencies handled differently (reserves check)
            
        # Global risk-free rate (approximate average of top economies)
        # Simplified: 3%
        i_foreign = 0.03
        
        # Expected depreciation (based on inflation diff and trade balance)
        # High inflation -> expect depreciation
        inflation_diff = nation.inflation_rate - 0.02
        expected_depreciation = inflation_diff + (0 if nation.trade_balance > 0 else 0.05)
        
        # Required return to hold currency
        required_rate = i_foreign + expected_depreciation + 0.02 # Risk premium
        
        # If actual rate is significantly lower, capital flight triggers attack
        if nation.currency.interest_rate < required_rate - 0.02:
            # Probability scales with gap
            gap = required_rate - nation.currency.interest_rate
            prob = min(0.5, gap * 5)
            return random.random() < prob
            
        return False

    def trigger_contagion(self, source_nation: Nation):
        """Spread financial crisis to trade partners."""
        partners = self.get_nation_trade_partners(source_nation.id)
        # We need access to nation objects, but this method doesn't have the list.
        # We can't easily look them up without passing the list or storing it.
        # 'simulate_debt_crisis' is called from world.py which has the list.
        # But here we are inside Economy class.
        # We'll rely on the fact that we processed trade earlier and have IDs.
        # Wait, we need to modify the partners.
        # We can't do it here easily if we don't have the nation objects.
        # I will change simulate_debt_crisis to accept 'nations' list or handle it in world.py.
        # Actually, simulate_debt_crisis takes 'nation'.
        # I will add 'nations' to simulate_debt_crisis signature in world.py call.
        pass
    
    def get_global_trade_volume(self) -> float:
        """Calculate total global trade volume."""
        return sum(self.trade_volumes.values())
    
    def get_nation_trade_partners(self, nation_id: int) -> List[int]:
        """Get list of nation's trade partners."""
        partners = []
        for (a, b) in self.trade_agreements:
            if a == nation_id:
                partners.append(b)
            elif b == nation_id:
                partners.append(a)
        return partners

