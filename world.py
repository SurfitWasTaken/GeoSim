"""
World simulation orchestration.
Manages nations, global systems, and turn-by-turn mechanics.
"""

from typing import List, Dict, Tuple
import random
import numpy as np

from nation import Nation, Currency
from economy import GlobalEconomy
from events import EventSystem
from combat import WarSystem
from geography import HexGrid, TerrainType
from diplomacy import UnitedNations
from logger import setup_logger

logger = setup_logger()
from config import SimulationConfig, GOVERNMENT_TYPES, NATION_NAME_PARTS
from viz import Visualizer


class World:
    """Global simulation state and orchestration."""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.nations: List[Nation] = []
        self.step = 0
        
        # Global systems
        self.economy = GlobalEconomy(config)
        self.events = EventSystem(config)
        self.combat = WarSystem(config)
        self.un = UnitedNations(config)
        self.visualizer = Visualizer(config)
        
        # Global state
        self.climate_index = 0.0
        self.cumulative_carbon = 0.0
        self.tipping_points_triggered = set()
        self.nuclear_winter_active = False
        
        # Initialize geography
        self.hex_grid = HexGrid(config.world_width, config.world_height)
        
        # Initialize world
        self._initialize_nations()
        self._initialize_geography()
    
    def _initialize_nations(self):
        """Create initial nations with realistic distributions."""
        for i in range(self.config.num_nations):
            # Generate name
            name = self._generate_nation_name()
            
            # Random government type (weighted toward democracies/autocracies)
            gov_weights = [0.35, 0.35, 0.1, 0.15, 0.05]  # D, A, Th, Te, An
            gov_type = random.choices(list(GOVERNMENT_TYPES.keys()), weights=gov_weights)[0]
            
            # Population (log-normal distribution)
            pop_mean = np.log(20e6)
            pop = np.random.lognormal(pop_mean, 1.0)
            pop = np.clip(pop, self.config.pop_min, self.config.pop_max)
            
            # GDP (correlated with population, log-normal)
            gdp_per_capita = np.random.lognormal(np.log(15000), 1.2)
            gdp = pop * gdp_per_capita
            gdp = np.clip(gdp, self.config.gdp_min, self.config.gdp_max)
            
            # Technology (normal distribution)
            tech = np.clip(random.gauss(40, 15), self.config.tech_min, self.config.tech_max)
            
            # Military (based on GDP)
            mil_spending = gdp * random.uniform(0.01, 0.05)
            mil_power = {
                "army": random.uniform(20, 50),
                "navy": random.uniform(10, 40),
                "air": random.uniform(10, 40),
                "nuclear": 0
            }
            
            # Health (correlated with GDP/capita)
            health = 40 + (gdp_per_capita / 1000) + random.uniform(-10, 10)
            health = np.clip(health, self.config.health_min, self.config.health_max)
            
            # Ideology (normal distribution)
            ideology = random.gauss(0, 40)
            ideology = np.clip(ideology, -100, 100)
            
            # Stability
            stability = GOVERNMENT_TYPES[gov_type]["stability_base"] + random.uniform(-15, 15)
            stability = np.clip(stability, 0, 100)
            
            # Currency
            currency_name = f"{name[:3].upper()}"
            
            # Random currency regime
            regime_roll = random.random()
            if regime_roll < 0.7:
                regime = "floating"
            elif regime_roll < 0.9:
                regime = "pegged"
            else:
                regime = "gold"
                
            currency = Currency(name=currency_name, regime=regime)
            if regime == "gold":
                currency.gold_reserves = gdp * 0.1  # Initial gold reserves
            elif regime == "pegged":
                currency.peg_target = 1.0  # Peg to 1.0 initially
            
            nation = Nation(
                id=i,
                name=name,
                government_type=gov_type,
                population=pop,
                gdp=gdp,
                technology=tech,
                military_power=mil_power,
                health=health,
                ideology=ideology,
                stability=stability,
                currency=currency
            )
            
            self.nations.append(nation)
    
    def _generate_nation_name(self) -> str:
        """Generate realistic procedural nation name."""
        if random.random() < 0.3:
            # Compound name with prefix
            prefix = random.choice(NATION_NAME_PARTS["prefixes"])
            root = random.choice(NATION_NAME_PARTS["roots"])
            return f"{prefix} {root}"
        else:
            # Simple name
            root = random.choice(NATION_NAME_PARTS["roots"])
            if random.random() < 0.5:
                suffix = random.choice(NATION_NAME_PARTS["suffixes"])
                return f"{root}{suffix}"
            return root
    
    def _initialize_geography(self):
        """Assign territory tiles and resources to nations using HexGrid."""
        self.grid = np.zeros((self.config.world_height, self.config.world_width), dtype=int) - 1
        
        # Generate terrain
        self.hex_grid.generate_terrain(seed=42) # Fixed seed for now, or use config seed
        
        logger.info("Generating terrain and placing nations...")
        
        for nation in self.nations:
            # Random starting position (prefer PLAINS)
            attempts = 0
            while attempts < 100:
                start_x = random.randint(0, self.config.world_width - 1)
                start_y = random.randint(0, self.config.world_height - 1)
                
                if self.grid[start_y, start_x] == -1 and \
                   self.hex_grid.terrain[start_y, start_x] != TerrainType.OCEAN:
                    
                    # Claim territory
                    tiles = self._claim_tiles(self.grid, start_x, start_y, 10, nation.id)
                    nation.territory_tiles = tiles
                    
                    # Assign resources based on terrain
                    self._assign_resources(nation)
                    
                    # Initialize Hubbert curve tracking
                    nation.resources_initial = nation.resources.copy()
                    nation.resources_extracted = {k: 0.0 for k in nation.resources}
                    break
                
                attempts += 1
        
        # Determine coastal status
        for nation in self.nations:
            nation.is_coastal = False
            for (x, y) in nation.territory_tiles:
                neighbors = self.hex_grid.get_neighbors(x, y)
                for nx, ny in neighbors:
                    if self.hex_grid.terrain[ny, nx] == TerrainType.OCEAN:
                        nation.is_coastal = True
                        break
                if nation.is_coastal:
                    break
    
    def _assign_resources(self, nation: Nation):
        """Assign resources based on terrain types in territory."""
        nation.resources = {"oil": 0.0, "rare_earth": 0.0, "farmland": 0.0, "water": 0.0}
        
        for x, y in nation.territory_tiles:
            terrain = self.hex_grid.terrain[y, x]
            
            if terrain == TerrainType.PLAINS:
                nation.resources["farmland"] += random.uniform(5, 15)
                nation.resources["water"] += random.uniform(5, 10)
            elif terrain == TerrainType.FOREST:
                nation.resources["farmland"] += random.uniform(2, 8)
                nation.resources["water"] += random.uniform(8, 12)
            elif terrain == TerrainType.DESERT:
                nation.resources["oil"] += random.uniform(0, 20) # Oil in deserts
            elif terrain == TerrainType.MOUNTAIN:
                nation.resources["rare_earth"] += random.uniform(0, 20) # Minerals in mountains
                nation.resources["water"] += random.uniform(5, 15) # Headwaters
                
    def _claim_tiles(self, grid: np.ndarray, start_x: int, start_y: int, 
                    num_tiles: int, nation_id: int) -> List[Tuple[int, int]]:
        """BFS to claim contiguous tiles."""
        claimed = []
        queue = [(start_x, start_y)]
        grid[start_y, start_x] = nation_id
        claimed.append((start_x, start_y))
        
        while len(claimed) < num_tiles and queue:
            cx, cy = queue.pop(0)
            
            # Get hex neighbors
            neighbors = self.hex_grid.get_neighbors(cx, cy)
            random.shuffle(neighbors)
            
            for nx, ny in neighbors:
                if grid[ny, nx] == -1 and self.hex_grid.terrain[ny, nx] != TerrainType.OCEAN:
                    grid[ny, nx] = nation_id
                    claimed.append((nx, ny))
                    queue.append((nx, ny))
                    if len(claimed) >= num_tiles:
                        break
                        
        return claimed
    
    def simulate_step(self, step: int) -> Dict:
        """Execute one simulation step with all mechanics."""
        self.step = step
        events = []
        
        # 2. Economic Phase
        # a. Trade
        self.economy.update_trade_network(self.nations, self.hex_grid)
        self.economy.process_fdi_flows(self.nations)
        
        for nation in self.nations:
            if nation.population == 0:
                continue
            
            # Calculate GDP with trade multiplier
            trade_mult = self.economy.calculate_global_trade_multiplier(nation)
            nation.gdp = nation.calculate_gdp(self.config, trade_mult)
            
            # Monetary policy
            nation.manage_monetary_policy(self.config)
        
        # FDI flows
        self.economy.process_fdi_flows(self.nations)
        self.economy.process_colonial_relations(self.nations)
        
        # Exchange rates
        self.economy.update_exchange_rates(self.nations)
        
        # Debt crises
        for nation in self.nations:
            if nation.population > 0:
                if self.economy.simulate_debt_crisis(nation, self.nations):
                    events.append(f"DEBT CRISIS: {nation.name} defaults on sovereign debt")
        
        # b. R&D phase
        for nation in self.nations:
            if nation.population > 0:
                rd_spending = random.uniform(0.01, 0.04)  # 1-4% of GDP
                nation.invest_rd(rd_spending, self.config)
        
        # c. Military phase
        for nation in self.nations:
            if nation.population > 0:
                mil_spending = random.uniform(0.01, 0.05)  # 1-5% of GDP
                nation.build_military(mil_spending, self.config)
        
        # d. Diplomacy phase
        self._update_alliances()
        
        # e. Politics & Diplomacy
        events.extend(self._update_politics())
        events.extend(self._update_diplomacy())
        events.extend(self._update_intelligence())
        
        # f. Internal events Phase
        # Pass hex_grid for distance-based event logic (pandemics)
        new_events = self.events.process_events(self.nations, self.economy, self.step, self.hex_grid)
        events.extend(new_events)
        
        # g. Health & Population
        for nation in self.nations:
            if nation.population > 0:
                nation.update_health(self.config)
                nation.update_population(self.config)
                nation.update_stability(self.config)
        
        # h. War system
        war_triggers = self.combat.check_war_triggers(self.nations)
        for attacker_id, defender_id, cause in war_triggers:
            event = self.combat.initiate_war(attacker_id, defender_id, cause, self.nations)
            events.append(event)
        
        war_events = self.combat.resolve_wars(self.nations)
        events.extend(war_events)
        
        # Check nuclear winter
        if not self.nuclear_winter_active and self.combat.check_nuclear_winter():
            event = self.combat.apply_nuclear_winter(self.nations)
            events.append(event)
            self.nuclear_winter_active = True
        
        # i. Arms race
        self._process_arms_race()
        
        # Global constraints
        self._update_climate()
        self._extract_resources()
        
        # WTO Arbitration
        # Check for trade disputes (randomly for now, or based on trade imbalances)
        if random.random() < 0.1:
            living_nations = [n for n in self.nations if n.population > 0]
            if len(living_nations) >= 2:
                n1, n2 = random.sample(living_nations, 2)
                result = self.un.arbitrate_trade_dispute(n1, n2)
                if result != "settled":
                    events.append(f"WTO RULING: {result} wins trade dispute")
                # Winner gets boost, loser gets penalty
                winner = n1 if n1.name == result else n2
                loser = n2 if n1.name == result else n1
                winner.gdp *= 1.01
                loser.gdp *= 0.99
        
        # Space race
        self._update_space_race()
        
        # Migration
        self._process_migration()
        
        return {
            "step": step,
            "events": events,
            "global_stats": {
                "living_nations": sum(1 for n in self.nations if n.population > 0),
                "global_gdp": sum(n.gdp for n in self.nations if n.population > 0),
                "global_population": sum(n.population for n in self.nations if n.population > 0),
                "climate_index": self.climate_index,
                "nuclear_detonations": self.combat.nuclear_detonations,
                "global_trade_volume": self.economy.get_global_trade_volume()
            },
            "nations": [n.to_dict() for n in self.nations if n.population > 0],
            "active_wars": [war.copy() for war in self.combat.active_wars]
        }
    
    def _update_climate(self):
        """Update global climate state and effects."""
        # Calculate global emissions
        total_gdp = sum(n.gdp for n in self.nations if n.population > 0)
        total_extraction = sum(
            nation.resources_extracted.get("oil", 0) * 10  # Oil emits more
            for nation in self.nations if nation.population > 0
        )
        
        # Green tech reduces emissions
        green_reduction = 0.0
        for nation in self.nations:
            if nation.population > 0 and nation.technology > 80:
                # High-tech nations transition to renewables
                green_tech_factor = (nation.technology - 80) / 20.0  # 0-1 scale
                nation_emission = nation.gdp * self.config.climate_gdp_factor
                reduction = nation_emission * green_tech_factor * 0.5  # Up to 50% reduction
                green_reduction += reduction
        
        global_emissions = (total_gdp * self.config.climate_gdp_factor +
                           total_extraction * self.config.climate_resource_factor)
        global_emissions -= green_reduction
        
        self.cumulative_carbon += max(0, global_emissions)
        
        # Map to actual temperature rise
        # IPCC: ~3.7 trillion tons CO2 = ~2°C rise
        # climate_index represents proportion of budget used
        budget_fraction = self.cumulative_carbon / self.config.carbon_budget_2c
        temperature_rise = budget_fraction * self.config.climate_temp_scaling
        
        # Update climate index to represent temperature (°C above pre-industrial)
        self.climate_index = temperature_rise
        
        # Check Carbon Budget Exhaustion
        if budget_fraction > 1.0 and "budget_exhausted" not in self.tipping_points_triggered:
            self.tipping_points_triggered.add("budget_exhausted")
            logger.warning(f"CARBON BUDGET EXHAUSTED! Temperature rise: {temperature_rise:.1f}°C")
        
        # Check Tipping Points (temperature-based)
        if "permafrost" not in self.tipping_points_triggered and temperature_rise > 1.5:
            self.tipping_points_triggered.add("permafrost")
            logger.warning("TIPPING POINT: Permafrost melt triggered! Methane release accelerates warming.")
            self.cumulative_carbon += 200e9  # Burst release
            
        if "amazon" not in self.tipping_points_triggered and temperature_rise > 2.0:
            self.tipping_points_triggered.add("amazon")
            logger.warning("TIPPING POINT: Amazon dieback triggered! Carbon sink lost.")
            
        if "ice_sheets" not in self.tipping_points_triggered and temperature_rise > 2.5:
            self.tipping_points_triggered.add("ice_sheets")
            logger.warning("TIPPING POINT: Ice sheet collapse! Accelerated sea-level rise.")
            
        # Apply effects
        for nation in self.nations:
            if nation.population == 0: continue
            
            # 1. Sea Level Rise (Coastal Damage and Tile Loss)
            if nation.is_coastal:
                # GDP damage scales with warming
                damage = 0.001 * (temperature_rise ** 2)
                nation.gdp *= (1 - damage)
                
                # Lose coastal tiles at high temp rise (>2°C)
                if temperature_rise > 2.0 and self.step % 10 == 0:  # Every 10 steps
                    # Remove 1 tile
                    if len(nation.territory_tiles) > 1:  # Don't eliminate entirely from climate
                        # Find coastal tile (adjacent to ocean)
                        coastal_tiles = []
                        for tx, ty in nation.territory_tiles:
                            neighbors = self.hex_grid.get_neighbors(tx, ty)
                            for nx, ny in neighbors:
                                if self.hex_grid.terrain[ny, nx] == TerrainType.OCEAN:
                                    coastal_tiles.append((tx, ty))
                                    break
                        
                        if coastal_tiles:
                            lost_tile = random.choice(coastal_tiles)
                            nation.territory_tiles.remove(lost_tile)
                            # Update grid
                            x, y = lost_tile
                            self.grid[y, x] = -1  # Unclaimed
                            # Lose associated resources
                            for resource in ["farmland", "water"]:
                                if resource in nation.resources:
                                    nation.resources[resource] *= 0.95
                
                # Island nation threat (small territory + coastal)
                if len(nation.territory_tiles) < 5:
                    nation.stability -= temperature_rise * 2
                    if temperature_rise > 3.0:
                        nation.population *= 0.95  # Land loss migration
            
            # 2. Farmland Degradation
            # Tropics suffer more than temperate
            # Simplified: Random check based on temperature rise
            degradation = 0.005 * temperature_rise
            if "farmland" in nation.resources:
                nation.resources["farmland"] *= (1 - degradation)
                
            # 3. Disasters
            if random.random() < 0.01 * temperature_rise:
                self.events.events.append(f"CLIMATE: Extreme weather hits {nation.name}")
                nation.gdp *= 0.98
                nation.population *= 0.995
    
    def _update_alliances(self):
        """Update diplomatic alliances based on shared interests."""
        for i, nation_a in enumerate(self.nations):
            if nation_a.population == 0:
                continue
            
            for nation_b in self.nations[i+1:]:
                if nation_b.population == 0:
                    continue
                
                # Alliance cap: Maximum 10 alliances per nation
                a_has_capacity = len(nation_a.alliances) < 10
                b_has_capacity = len(nation_b.alliances) < 10
                
                # Alliance probability (Mutual Consent Required)
                # Check A's willingness
                proximity_a = 1 - abs(nation_a.ideology - nation_b.ideology) / 200
                trade_a = len(self.economy.get_nation_trade_partners(nation_a.id))
                prob_a = proximity_a * 0.02 + trade_a * 0.001
                
                # Check B's willingness
                proximity_b = 1 - abs(nation_b.ideology - nation_a.ideology) / 200
                trade_b = len(self.economy.get_nation_trade_partners(nation_b.id))
                prob_b = proximity_b * 0.02 + trade_b * 0.001
                
                if random.random() < prob_a and random.random() < prob_b:
                    if nation_b.id not in nation_a.alliances and a_has_capacity and b_has_capacity:
                        nation_a.alliances.add(nation_b.id)
                        nation_b.alliances.add(nation_a.id)
                elif random.random() < 0.02:  # Increased decay from 0.01 to 0.02
                    # Break alliance - higher chance with low proximity
                    if nation_b.id in nation_a.alliances:
                        # More likely to break if ideologies drift apart
                        if random.random() < (1 - proximity_a):
                            nation_a.alliances.discard(nation_b.id)
                            nation_b.alliances.discard(nation_a.id)

    
    def _update_politics(self) -> List[str]:
        """Update domestic politics for all nations."""
        events = []
        for nation in self.nations:
            if nation.population > 0:
                nation.politics.update()
                
                # Check for coups
                if nation.politics.check_coup_risk():
                    logger.warning(f"COUP: Military/Faction coup in {nation.name}!")
                    nation.stability -= 30
                    nation.government_type = "Autocracy"
                    events.append(f"COUP: Government overthrown in {nation.name}")
        return events

    def _update_diplomacy(self) -> List[str]:
        """Update UN and international relations."""
        events = []
        self.un.update_security_council(self.nations)
        
        # Random UN resolution proposal
        if random.random() < 0.1: # 10% chance per step
            living_nations = [n for n in self.nations if n.population > 0]
            if len(living_nations) >= 2:
                proposer = random.choice(living_nations)
                # Filter out proposer from potential targets
                potential_targets = [n for n in living_nations if n.id != proposer.id]
                
                if potential_targets:
                    target = random.choice(potential_targets)
                    res_type = random.choice(["sanctions", "aid", "condemnation"])
                    passed = self.un.propose_resolution(proposer, res_type, target, self.nations)
                    
                    status = "PASSED" if passed else "FAILED/VETOED"
                    events.append(f"UN RESOLUTION: {res_type.upper()} against {target.name} proposed by {proposer.name} - {status}")
        return events

    def _update_intelligence(self) -> List[str]:
        """Update espionage activities."""
        from intelligence import MissionType
        events = []
        
        for nation in self.nations:
            if nation.population > 0 and nation.intelligence.budget > 0:
                # Random mission attempt
                if random.random() < 0.05:
                    potential_targets = [n for n in self.nations if n.id != nation.id and n.population > 0]
                    if potential_targets:
                        target = random.choice(potential_targets)
                        mission = random.choice(list(MissionType))
                        
                        result = nation.intelligence.conduct_operation(target, mission)
                        
                        if result["success"]:
                            # Apply effects
                            if mission == MissionType.STEAL_TECH:
                                nation.technology += 1
                                logger.info(f"SPY: {nation.name} stole tech from {target.name}")
                            elif mission == MissionType.SABOTAGE_INFRASTRUCTURE:
                                target.gdp *= 0.99
                                logger.info(f"SPY: {nation.name} sabotaged {target.name}")
                                
                        if result["detected"]:
                            # Diplomatic fallout
                            logger.warning(f"SPY DETECTED: {nation.name} caught spying on {target.name}")
                            events.append(f"SCANDAL: {nation.name} spies caught in {target.name}")
                            target.relations_with[nation.id] = target.relations_with.get(nation.id, 0) - 50
        return events
    
    def _process_arms_race(self):
        """Nations respond to neighbors' military buildup."""
        for nation in self.nations:
            if nation.population == 0:
                continue
            
            # Check neighbors' military strength (simplified: random sample)
            potential_neighbors = [n for n in self.nations if n.population > 0 and n.id != nation.id]
            if not potential_neighbors:
                continue
                
            sample_size = min(5, len(potential_neighbors))
            neighbors = random.sample(potential_neighbors, sample_size)
            
            avg_neighbor_mil = np.mean([n.get_total_military_power() for n in neighbors])
            
            # If falling behind, increase military spending
            if nation.get_total_military_power() < avg_neighbor_mil * 0.7:
                extra_spending = random.uniform(0.01, 0.03)
                nation.build_military(extra_spending, self.config)
    
    # Removed duplicate _update_climate method
    
    def _extract_resources(self):
        """Extract resources using Hubbert Curve logic."""
        for nation in self.nations:
            if nation.population == 0:
                continue
            
            for resource in ["oil", "rare_earth"]:
                if resource in nation.resources and nation.resources[resource] > 0:
                    total_initial = nation.resources_initial.get(resource, nation.resources[resource] * 2) # Fallback
                    extracted_so_far = nation.resources_extracted.get(resource, 0.0)
                    
                    if total_initial <= 0: 
                        continue
                        
                    # Calculate depletion fraction
                    depletion_fraction = extracted_so_far / total_initial
                    
                    # Hubbert Peak Logic: Production peaks at ~40% depletion (Asymmetric)
                    # Skewed distribution: C * d^a * (1-d)^b
                    # With a=2, b=3, peak is at 0.4.
                    # Max value is approx 0.03456. Scaling factor ~29.
                    d_clamped = max(0.01, min(0.99, depletion_fraction))
                    production_curve_factor = 29.0 * (d_clamped ** 2) * ((1 - d_clamped) ** 3)
                    
                    # Base extraction rate modified by curve
                    extraction_rate = self.config.resource_depletion_rate * production_curve_factor
                    
                    # Tech efficiency reduces waste (extracts more utility per unit) OR increases rate?
                    # Usually tech increases rate of extraction.
                    extraction_rate *= (1 + nation.technology / 100 * 0.5)
                    
                    extracted_amount = total_initial * extraction_rate
                    
                    # Cap at remaining
                    extracted_amount = min(extracted_amount, nation.resources[resource])
                    
                    nation.resources[resource] -= extracted_amount
                    nation.resources_extracted[resource] = extracted_so_far + extracted_amount
                    
                    # Resource extraction boosts GDP
                    # Value depends on scarcity (global remaining vs initial)
                    # Simplified: fixed value
                    nation.gdp += extracted_amount * random.uniform(1e6, 5e6)
    
    def _update_space_race(self):
        """Update space programs for high-tech nations."""
        for nation in self.nations:
            if (nation.population > 0 and 
                nation.technology >= self.config.tech_space_threshold and
                not nation.has_space_program):
                
                if random.random() < 0.1:  # 10% chance per year
                    nation.has_space_program = True
                    nation.technology += 5  # Boost from space tech
            
            # Space programs provide intelligence bonuses
            if nation.has_space_program:
                nation.military_power["air"] += 0.5  # Satellite intel
    
    def _process_migration(self):
        """Process migration flows between nations."""
        for nation in self.nations:
            if nation.population == 0:
                continue
            
            # Push factors: low stability, climate, war
            if nation.stability < 40 or nation.is_at_war or self.climate_index > 70:
                emigration_rate = random.uniform(0.001, 0.01)
                emigrants = nation.population * emigration_rate
                nation.population -= emigrants
                
                # Find destination (high GDP/capita, stable)
                destinations = [(n, n.get_gdp_per_capita() * n.stability) 
                              for n in self.nations if n.population > 0 and n.id != nation.id]
                
                if destinations:
                    destinations.sort(key=lambda x: x[1], reverse=True)
                    dest = destinations[0][0]
                    dest.population += emigrants * 0.7  # Some lost in transit
    
    def print_summary(self, step: int):
        """Print periodic summary table."""
        living = [n for n in self.nations if n.population > 0]
        living.sort(key=lambda n: n.gdp, reverse=True)
        
        print(f"\n{'='*120}")
        print(f"STEP {step} SUMMARY - {len(living)} nations surviving")
        print(f"{'='*120}")
        print(f"{'Nation':<20} {'Pop(M)':<10} {'GDP($T)':<10} {'Tech':<6} {'Mil':<6} {'Gov':<12} {'Health':<7} {'Allies':<7} {'FX Rate':<8}")
        print(f"{'-'*120}")
        
        if living:
            for nation in living[:15]:  # Top 15
                print(f"{nation.name:<20} "
                      f"{nation.population/1e6:>9.1f} "
                      f"{nation.gdp/1e12:>9.2f} "
                      f"{nation.technology:>5.0f} "
                      f"{nation.get_total_military_power():>5.0f} "
                      f"{nation.government_type:<12} "
                      f"{nation.health:>6.0f} "
                      f"{len(nation.alliances):>6} "
                      f"{nation.currency.exchange_rate:>7.2f}")
        else:
            print("No surviving nations.")
        
        print(f"\nGlobal Stats: GDP=${sum(n.gdp for n in living)/1e12:.1f}T, "
              f"Pop={sum(n.population for n in living)/1e9:.2f}B, "
              f"Climate={self.climate_index:.0f}, "
              f"Wars={len(self.combat.active_wars)}")
    
    def generate_map(self, step: int):
        """Generate world map visualization."""
        self.visualizer.create_world_map(self.nations, step, self.climate_index, self.hex_grid)
    
    def generate_final_report(self):
        """Generate comprehensive end-of-simulation report."""
        living = [n for n in self.nations if n.population > 0]
        extinct_count = self.config.num_nations - len(living)
        
        print(f"\n{'='*80}")
        print("FINAL SIMULATION REPORT")
        print(f"{'='*80}\n")
        
        print(f"Simulation Duration: {self.config.num_steps} steps")
        print(f"Surviving Nations: {len(living)} / {self.config.num_nations}")
        print(f"Extinct Nations: {extinct_count}")
        print(f"Nuclear Detonations: {self.combat.nuclear_detonations}")
        print(f"Total Wars: {len(self.combat.war_history)}")
        print(f"Climate Index: {self.climate_index:.1f}")
        print(f"Global Trade Volume: ${self.economy.get_global_trade_volume()/1e12:.2f}T\n")
        
        if living:
            print("WINNERS:\n")
            
            # Highest GDP
            richest = max(living, key=lambda n: n.gdp)
            print(f"  Wealthiest: {richest.name} (${richest.gdp/1e12:.2f}T GDP)")
            
            # Highest GDP/capita
            richest_pc = max(living, key=lambda n: n.get_gdp_per_capita())
            print(f"  Highest GDP/capita: {richest_pc.name} (${richest_pc.get_gdp_per_capita():,.0f})")
            
            # Most advanced
            tech_leader = max(living, key=lambda n: n.technology)
            print(f"  Tech Leader: {tech_leader.name} (Tech {tech_leader.technology:.0f})")
            
            # Military superpower
            mil_power = max(living, key=lambda n: n.get_total_military_power())
            print(f"  Military Superpower: {mil_power.name} (Power {mil_power.get_total_military_power():.0f})")
            
            # Calculate global inequality (Gini coefficient approximation)
            gdp_per_capitas = sorted([n.get_gdp_per_capita() for n in living])
            n = len(gdp_per_capitas)
            if n > 0:
                gini = (2 * sum((i+1) * gdp for i, gdp in enumerate(gdp_per_capitas))) / (n * sum(gdp_per_capitas)) - (n + 1) / n
                print(f"\n  Global Inequality (Gini): {gini:.3f}")
        else:
            print("No surviving nations.")
        
        print(f"\n{'='*80}\n")