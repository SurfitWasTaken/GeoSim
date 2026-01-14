# Realistic Geopolitical & Economic Simulation

A comprehensive Python simulation system modeling sovereign nations with realistic macroeconomic dynamics, trade networks, military conflicts, and emergent behaviors. Built on empirical data and established economic models including Solow-Swan growth theory, Cobb-Douglas production functions, Lanchester combat equations, and IPCC climate scenarios.

## Features

### Core Systems

- **50+ Sovereign Nations** (configurable) with diverse government types, ideologies, and economic systems
- **Realistic Macroeconomics**: Cobb-Douglas production functions, endogenous growth, demographic transitions, labor markets
- **Global Trade Networks**: Multilateral agreements with Ricardian comparative advantage, gravity model trade flows
- **Currency Markets**: Floating exchange rates, inflation dynamics, Taylor rule monetary policy, gold standard option
- **Foreign Direct Investment**: Capital flows with risk-adjusted returns, technology transfer, economic dependencies
- **Military Conflicts**: Lanchester-style combat with tech multipliers, nuclear weapons, war exhaustion
- **Climate Change**: IPCC-calibrated emissions, resource depletion, migration triggers, environmental costs
- **Pandemics**: COVID-19-inspired disease spread with R0, lethality, vaccine development timelines
- **International Institutions**: UN-like security council with veto powers, WTO trade arbitration
- **Space Race**: Orbital assets providing intelligence and economic bonuses for advanced nations

### Realism Features

- **Empirical Calibration**: Parameters based on UN population projections, World Bank GDP data, SIPRI military spending, WHO health indices
- **Stochastic Events**: Elections, coups, natural disasters, tech breakthroughs, corruption scandals, debt defaults
- **Emergent Behaviors**: Inequality amplification, arms races, alliance formation, colonial influence, refugee crises
- **Economic Crises**: Sovereign defaults, currency devaluations, speculative attacks, hyperinflation
- **Demographic Transitions**: Aging populations in developed nations, youth bulges in developing countries

## Installation

```bash
# Clone or download the repository
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Simulation

```bash
python main.py --nations 50 --steps 500 --seed 42
```

### Advanced Options

```bash
python main.py \
  --nations 100 \
  --steps 1000 \
  --seed 42 \
  --realism-level high \
  --enable-gold-standard \
  --output-dir results/
```

### Command-Line Arguments

- `--nations N`: Number of countries (default: 50)
- `--steps T`: Simulation duration (default: 500)
- `--seed S`: Random seed for reproducibility
- `--realism-level {low,medium,high}`: Parameter strictness
- `--enable-gold-standard`: Allow nations to adopt gold standard
- `--output-dir PATH`: Output directory (default: output/)

## Output Files

### Generated Files

- `simulation.json`: Complete history of all simulation steps with economic metrics and events
- `world_map_step_XXXX.png`: Periodic visualizations (every 50 steps) showing:
  - Territorial control
  - Military power heatmap
  - Public health distribution
  - Economic rankings and climate index
- Console output: Periodic summaries every 10 steps with nation statistics

### Final Report

End-of-simulation report includes:
- Surviving nations and extinctions
- Winners by GDP, GDP/capita, technology, military power
- Total wars and nuclear detonations
- Global trade volume and climate index
- Global inequality (Gini coefficient)

## Architecture

### Module Structure

```
├── main.py              # Entry point and CLI
├── config.py            # Global parameters and constants
├── nation.py            # Nation model with attributes and behaviors
├── economy.py           # Global economic systems (trade, FDI, institutions)
├── events.py            # Random events (elections, disasters, pandemics)
├── combat.py            # Warfare resolution (Lanchester equations)
├── world.py             # World orchestration and turn mechanics
├── viz.py               # Matplotlib visualizations
└── test_simulation.py   # Pytest test suite
```

### Economic Models

**GDP Calculation** (Augmented Solow-Swan):
```
Y = A × K^α × (h×L)^(1-α)

Where:
- A = TFP (tech + institutions)
- K = Capital stock
- h = Human capital (health/education)
- L = Working-age population
- α = 0.33 (capital share)
```

**Trade Gravity Model**:
```
Trade_ij ∝ (GDP_i × GDP_j) / Distance²
```

**Exchange Rate Dynamics**:
```
ΔER = f(inflation_diff, balance_of_payments, interest_rate_diff)
```

### Combat Resolution

Uses modified Lanchester square law with technology, logistics, and morale modifiers:

```
Casualties_A = Strength_B² × intensity
Casualties_B = Strength_A² × intensity × tech_ratio × logistics_ratio
```

## Testing

Run the test suite:

```bash
pytest test_simulation.py -v
```

Tests include:
- Nation mechanics (GDP, population, technology, military)
- Economic systems (trade, FDI, exchange rates)
- Warfare (triggers, combat resolution)
- Integration tests (full simulation, pandemic, crisis scenarios)
- Reproducibility verification

## Realism Calibration

### Parameter Sources

- **Population Growth**: UN World Population Prospects (1.2% ± 0.8%)
- **GDP Growth**: Solow-Swan model with empirical TFP growth (~1.5%/year)
- **Military Spending**: SIPRI data (1-5% of GDP, average ~2%)
- **Technology**: Normalized R&D efficiency based on OECD statistics
- **Health**: WHO indices scaled 0-100
- **Inflation**: Central bank targeting (2% ± 1%)
- **Conflict Probability**: Uppsala Conflict Data Program (~2% base rate)
- **Pandemic Parameters**: COVID-19 calibration (R0=2.5, IFR=1%)
- **Climate Change**: IPCC RCP scenarios for emissions and impacts

### Emergent Behaviors

The simulation produces realistic patterns:
- **Democratic Peace Theory**: Democracies less likely to fight each other
- **Thucydides Trap**: Rising powers challenge dominant powers
- **Resource Curse**: Oil-rich nations experience governance challenges
- **Demographic Dividend**: Young populations boost growth
- **Middle Income Trap**: Nations struggle to transition to high-income status
- **Arms Race Dynamics**: Security dilemmas lead to mutual escalation

## Configuration Tuning

Adjust realism parameters in `config.py`:

- **Economic**: `capital_share_alpha`, `tfp_growth_base`, `depreciation_rate`
- **Trade**: `trade_comparative_advantage_boost`, `fdi_return_rate`
- **Military**: `military_gdp_cost`, `war_base_probability`
- **Climate**: `climate_gdp_factor`, `climate_migration_threshold`
- **Events**: `event_pandemic_prob`, `event_coup_base_prob`

## Performance

- ~1-2 seconds per step for 50 nations on modern hardware
- Memory usage: ~500MB for 500-step simulation
- Visualization generation: ~0.5 seconds per map

## File Structure

All 11 files required for the simulation:

1. **main.py** - Entry point with CLI argument parsing
2. **config.py** - Configuration constants and parameters
3. **nation.py** - Nation class with economic/military/political systems
4. **economy.py** - Global trade, FDI, currency markets, institutions
5. **events.py** - Random events (elections, disasters, pandemics, etc.)
6. **combat.py** - Warfare system with Lanchester equations
7. **world.py** - World orchestration and turn-by-turn simulation
8. **viz.py** - Matplotlib visualization generation
9. **test_simulation.py** - Pytest test suite
10. **requirements.txt** - Python dependencies
11. **README.md** - This documentation file

## Quick Start

```bash
# 1. Ensure all 11 files are in the same directory
# 2. Install dependencies
pip install numpy matplotlib tqdm pytest

# 3. Run a quick test
python main.py --nations 20 --steps 100 --seed 42

# 4. Run full simulation
python main.py --nations 50 --steps 500 --seed 42

# 5. Run tests
pytest test_simulation.py -v
```

## Example Output

```
========================================================
STEP 100 SUMMARY - 47 nations surviving
========================================================
Nation               Pop(M)    GDP($T)   Tech  Mil   Gov          Health Allies FX Rate
--------------------------------------------------------
Greater Lumeria        89.2      12.45     78    85  Technocracy      82      8    1.15
Solvaria               67.3       9.23     72    78  Democracy        79      6    0.98
North Drakos          112.5       8.67     65    82  Autocracy        71      4    1.32
...

Global Stats: GDP=$487.3T, Pop=3.45B, Climate=42, Wars=2
```

## Future Enhancements

Potential extensions:
- Sub-national regions and civil wars
- International organizations (EU, ASEAN, NATO analogues)
- Commodity markets (oil, food, rare earths)
- Cyber warfare and information operations
- AI/automation economic transitions
- More sophisticated climate models with tipping points

## License

MIT License - See LICENSE file for details

## Citation

If using this simulation for research:

```bibtex
@software{geopolitical_sim,
  title={Realistic Geopolitical and Economic Simulation},
  author={Anonymous},
  year={2024},
  url={https://github.com/example/geosim}
}
```

## Acknowledgments

Built on established models from:
- Solow-Swan growth theory
- Cobb-Douglas production functions
- Gravity model of trade (Tinbergen, 1962)
- Lanchester combat equations
- IPCC climate scenarios
- Empirical data from UN, World Bank, IMF, WHO, SIPRI

## Troubleshooting

**Import Errors**: Ensure all 11 .py files are in the same directory

**Missing Dependencies**: Run `pip install -r requirements.txt`

**Visualization Errors**: Install matplotlib with `pip install matplotlib`

**Slow Performance**: Reduce `--nations` or `--steps` for faster runs

**Memory Issues**: Reduce visualization frequency or nation count

## Contact

For issues, questions, or contributions, please open an issue on the repository.