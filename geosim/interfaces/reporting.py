import json
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template
from datetime import datetime

class ReportGenerator:
    """Generates HTML reports for simulation results."""
    
    def __init__(self, config):
        self.config = config
        self.template = self._get_template()
        
    def generate_report(self, history: List[Dict[str, Any]], output_dir: Path):
        """Generate comprehensive HTML report."""
        
        # Process data for charts/tables
        global_stats = [h['global_stats'] for h in history]
        events = []
        for h in history:
            step = h['step']
            for event in h['events']:
                # Parse event string if needed, or just use as is
                # Assuming event is a string
                events.append({"step": step, "message": event})
        
        # Find all generated map images
        map_files = sorted(list(output_dir.glob("world_map_step_*.png")))
        
        # Filter out maps that are beyond the current simulation range (stale files)
        max_step = 0
        if history:
            max_step = history[-1]['step']
            
        valid_map_images = []
        for f in map_files:
            try:
                # Extract step number: world_map_step_0100.png -> 100
                step_str = f.name.replace('world_map_step_', '').replace('.png', '')
                step_num = int(step_str)
                # Allow +1 because history is 0-indexed but maps are 1-indexed (often)
                if step_num <= max_step + 1:
                    valid_map_images.append(f.name)
            except ValueError:
                continue
                
        map_images = valid_map_images
        
        # If no maps found, provide a placeholder or empty list
        if not map_images:
            map_images = []

        # Render template
        html_content = self.template.render(
            simulation_name="GeoSim AI Run",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            steps=len(history),
            final_stats=global_stats[-1] if global_stats else {},
            events=events,
            map_images=map_images,
            config=self.config
        )
        
        # Save report
        report_path = output_dir / "index.html"
        with open(report_path, "w") as f:
            f.write(html_content)
            
        return report_path

    def _get_template(self) -> Template:
        """Return Jinja2 template for the report."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ simulation_name }} - Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .card { margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .event-log { max-height: 500px; overflow-y: auto; font-family: monospace; font-size: 0.9em; }
        .stat-card { text-align: center; padding: 20px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #0d6efd; }
        .stat-label { color: #6c757d; text-transform: uppercase; font-size: 0.8em; }
        .map-container { text-align: center; }
        img { max-width: 100%; height: auto; border-radius: 5px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🌍 {{ simulation_name }}</span>
            <span class="navbar-text">{{ timestamp }}</span>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Key Metrics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-value">{{ steps }}</div>
                    <div class="stat-label">Total Steps</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-value">{{ final_stats.living_nations }}</div>
                    <div class="stat-label">Surviving Nations</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-value">${{ "%.2f"|format(final_stats.global_gdp / 1e12) }}T</div>
                    <div class="stat-label">Global GDP</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stat-card">
                    <div class="stat-value">{{ "%.2f"|format(final_stats.global_population / 1e9) }}B</div>
                    <div class="stat-label">Global Population</div>
                </div>
            </div>
        </div>

        <!-- Visualizations -->
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header fw-bold">Simulation Timeline</div>
                    <div class="card-body map-container">
                        <img src="timeline_analysis.png" alt="Timeline Analysis">
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header fw-bold">
                        World State History 
                        {% if map_images %}
                        (Step <span id="stepLabel">{{ map_images[-1] | replace('world_map_step_', '') | replace('.png', '') }}</span>)
                        {% endif %}
                    </div>
                    <div class="card-body map-container">
                        {% if map_images %}
                        <img id="worldMapImage" src="{{ map_images[-1] }}" alt="World Map">
                        <input type="range" class="form-range mt-3" min="0" max="{{ map_images|length - 1 }}" step="1" id="mapSlider" value="{{ map_images|length - 1 }}">
                        <div class="text-muted small mt-1">Drag slider to view history</div>
                        {% else %}
                        <div class="alert alert-warning">No map images found. Run with visualization enabled.</div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Event Log -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header fw-bold">Event Log</div>
                    <div class="card-body event-log">
                        <input type="text" id="eventSearch" class="form-control mb-2" placeholder="Search events...">
                        <div id="eventList">
                            {% for event in events|reverse %}
                            <div class="event-item border-bottom py-1">
                                <span class="badge bg-secondary">Step {{ event.step }}</span>
                                {{ event.message }}
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Simple search filter
        document.getElementById('eventSearch').addEventListener('keyup', function() {
            let filter = this.value.toLowerCase();
            let items = document.querySelectorAll('.event-item');
            items.forEach(function(item) {
                let text = item.textContent.toLowerCase();
                item.style.display = text.includes(filter) ? '' : 'none';
            });
        });

        // Map Slider
        {% if map_images %}
        const mapImages = {{ map_images | tojson }};
        const slider = document.getElementById('mapSlider');
        const image = document.getElementById('worldMapImage');
        const label = document.getElementById('stepLabel');

        slider.addEventListener('input', function() {
            const index = this.value;
            const filename = mapImages[index];
            image.src = filename;
            // Extract step number from filename
            const step = filename.replace('world_map_step_', '').replace('.png', '');
            label.textContent = step;
        });
        {% endif %}
    </script>
</body>
</html>
        """)
