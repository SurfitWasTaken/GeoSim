"""
Geopolitical Simulation System
Main entry point for running realistic world simulations with economic modeling,
trade networks, institutions, and emergent behaviors.
"""

import argparse
import json
import random
import time
from pathlib import Path
import numpy as np

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from world import World
from config import SimulationConfig
from logger import setup_logger
from reporting import ReportGenerator

logger = None
console = Console()

class NumpyEncoder(json.JSONEncoder):
    """Custom encoder for NumPy data types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        return super(NumpyEncoder, self).default(obj)

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for simulation configuration."""
    parser = argparse.ArgumentParser(
        description="Realistic geopolitical and economic simulation"
    )
    parser.add_argument(
        "--nations", type=int, default=50,
        help="Number of sovereign countries (default: 50)"
    )
    parser.add_argument(
        "--steps", type=int, default=500,
        help="Number of time steps to simulate (default: 500)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--realism-level", choices=["low", "medium", "high"], default="high",
        help="Realism parameter strictness (default: high)"
    )
    parser.add_argument(
        "--enable-gold-standard", action="store_true",
        help="Enable gold standard currency option"
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Directory for output files (default: output)"
    )
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
        help="Logging verbosity level (default: INFO)"
    )
    parser.add_argument(
        "--no-viz", action="store_true",
        help="Skip visualization generation for performance"
    )
    return parser.parse_args()


def create_dashboard(step, total_steps, stats, events):
    """Create a rich layout dashboard."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    
    # Header
    layout["header"].update(Panel(f"🌍 GeoSim AI - Step {step}/{total_steps}", style="bold blue"))
    
    # Stats Table
    table = Table(title="Global Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    if stats:
        table.add_row("Living Nations", str(stats.get("living_nations", 0)))
        table.add_row("Global GDP", f"${stats.get('global_gdp', 0)/1e12:.2f}T")
        table.add_row("Global Pop", f"{stats.get('global_population', 0)/1e9:.2f}B")
        table.add_row("Climate Index", f"{stats.get('climate_index', 0):.2f}")
    
    # Events Log
    event_text = "\n".join([f"• {e}" for e in events[-8:]]) if events else "No events yet."
    
    layout["main"].split_row(
        Layout(Panel(table, title="Stats"), ratio=1),
        Layout(Panel(event_text, title="Recent Events", style="yellow"), ratio=2)
    )
    
    # Footer (Progress is handled by Live context, so maybe just status)
    layout["footer"].update(Panel("Running simulation...", style="italic"))
    
    return layout

def main():
    """Main simulation loop with progress tracking and periodic reporting."""
    global logger
    args = parse_args()
    
    # Setup logger
    logger = setup_logger(level_name=args.log_level)
    
    # Set up random seed for reproducibility
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize configuration
    config = SimulationConfig(
        num_nations=args.nations,
        num_steps=args.steps,
        realism_level=args.realism_level,
        enable_gold_standard=args.enable_gold_standard,
        output_dir=output_dir
    )
    
    # Initialize world
    console.print(f"[bold green]Initializing world with {args.nations} nations...[/bold green]")
    world = World(config)
    
    # Simulation loop with rich dashboard
    history = []
    recent_events = []
    
    with Live(console=console, refresh_per_second=4) as live:
        for step in range(args.steps):
            # Execute turn mechanics
            step_data = world.simulate_step(step)
            history.append(step_data)
            
            # Update events
            if step_data.get("events"):
                # Clean up event strings if they are complex objects
                new_events = [str(e) for e in step_data["events"]]
                recent_events.extend(new_events)
                # Keep only last 20 for display buffer
                recent_events = recent_events[-20:]
            
            # Generate visualizations
            if not args.no_viz and (step + 1) % 50 == 0:
                world.generate_map(step + 1)
            
            # Update Dashboard
            dashboard = create_dashboard(
                step + 1, 
                args.steps, 
                step_data.get("global_stats", {}), 
                recent_events
            )
            live.update(dashboard)
            
            # Small delay for visual effect if running very fast (optional)
            # time.sleep(0.05)
    
    # Save full simulation history
    history_file = output_dir / "simulation.json"
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2, cls=NumpyEncoder)
    console.print(f"[bold green]Simulation history saved to {history_file}[/bold green]")
    
    # Generate final report
    console.print("[bold yellow]Generating final report...[/bold yellow]")
    
    # Timeline plots
    world.visualizer.plot_timeline_analysis(history, output_dir / "timeline_analysis.png")
    
    # HTML Report
    reporter = ReportGenerator(config)
    report_path = reporter.generate_report(history, output_dir)
    
    console.print(f"[bold green]Report generated at: {report_path}[/bold green]")
    console.print("[bold blue]Simulation complete![/bold blue]")


if __name__ == "__main__":
    main()