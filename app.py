import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np
from pathlib import Path
from PIL import Image
import os

# Page Config
st.set_page_config(
    page_title="GeoSim AI Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
OUTPUT_DIR = Path("output")
SIMULATION_FILE = OUTPUT_DIR / "simulation.json"

# --- Data Loading ---
@st.cache_data
def load_data():
    """Load and process simulation data."""
    if not SIMULATION_FILE.exists():
        st.error(f"Simulation file not found at {SIMULATION_FILE}")
        return None, None

    with open(SIMULATION_FILE, 'r') as f:
        data = json.load(f)

    # Flatten data for analysis
    steps_data = []
    nations_data = []
    
    for step_record in data:
        step = step_record['step']
        events = step_record.get('events', [])
        stats = step_record.get('global_stats', {})
        
        # Global Step Data
        step_row = {
            'step': step,
            'gdp': stats.get('global_gdp', 0),
            'pop': stats.get('global_population', 0),
            'wars': stats.get('active_wars_count', 0) if 'active_wars_count' in stats else stats.get('nuclear_detonations', 0), # Fallback/Proxy
            'climate': stats.get('climate_index', 0),
            'gini': stats.get('gini_coefficient', 0),
            'events': len(events)
        }
        steps_data.append(step_row)
        
        # Nation Data
        for n in step_record.get('nations', []):
            n_row = {
                'step': step,
                'id': n['id'],
                'name': n['name'],
                'gdp': n['gdp'],
                'pop': n['population'],
                'tech': n['technology'],
                'mil_army': n['military_power']['army'],
                'mil_navy': n['military_power']['navy'],
                'stability': n['stability'],
                'health': n['health'],
                'ideology': n['ideology'],
                'gov': n['government_type'],
                'at_war': n.get('is_at_war', False)
            }
            nations_data.append(n_row)

    df_steps = pd.DataFrame(steps_data)
    df_nations = pd.DataFrame(nations_data)
    
    return df_steps, df_nations, data

# --- Sidebar ---
st.sidebar.title("🌍 GeoSim Command")
df_steps, df_nations, raw_data = load_data()

if df_steps is not None:
    max_step = int(df_steps['step'].max())
    selected_step = st.sidebar.slider("Simulation Step", 0, max_step, max_step)
    
    # Filter data for current step
    current_step_stats = df_steps[df_steps['step'] == selected_step].iloc[0]
    current_nations = df_nations[df_nations['step'] == selected_step]
    
    # Nation Filter
    all_nations = sorted(df_nations['name'].unique())
    selected_nations = st.sidebar.multiselect("Select Nations for Analysis", all_nations)

# --- Main Content ---
st.title(f"GeoSim AI Simulation - Step {selected_step}")

if df_steps is None:
    st.stop()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🗺️ World Map", "📈 Analysis", "🕸️ Networks", "📜 Events"])

# --- Tab 1: Dashboard ---
with tab1:
    # Top Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Global GDP", f"${current_step_stats['gdp']/1e12:.2f}T")
    c2.metric("Population", f"{current_step_stats['pop']/1e9:.2f}B")
    c3.metric("Active Conflicts", f"{int(current_step_stats['wars'])}") # Placeholder name fix
    c4.metric("Climate Index", f"{current_step_stats['climate']:.4f}")

    # Charts
    st.subheader("Global Trends")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_gdp = px.line(df_steps, x="step", y="gdp", title="Global GDP History")
        fig_gdp.add_vline(x=selected_step, line_dash="dash", line_color="red")
        st.plotly_chart(fig_gdp, use_container_width=True)
        
    with chart_col2:
        fig_pop = px.line(df_steps, x="step", y="pop", title="Global Population History")
        fig_pop.add_vline(x=selected_step, line_dash="dash", line_color="red")
        st.plotly_chart(fig_pop, use_container_width=True)

# --- Tab 2: World Map ---
with tab2:
    st.header("Global Status Map")
    
    # Try to find map image for this step
    # Map steps might be every 2 steps
    # Find closest step <= selected_step that has a map matches pattern
    
    # Pattern: world_map_{step:04d}.png or world_map_step_{step}.png based on filename history
    # Let's check typical patterns
    
    map_path = None
    # Try exact match first (new format)
    candidate = OUTPUT_DIR / f"world_map_{selected_step:04d}.png"
    if candidate.exists():
        map_path = candidate
    else:
        # Try old format
        candidate = OUTPUT_DIR / f"world_map_step_{selected_step}.png"
        if candidate.exists():
            map_path = candidate
        else:
            # Fallback to closest previous
            # This is a bit brute force but safe for small steps
            for i in range(selected_step, -1, -1):
                c1 = OUTPUT_DIR / f"world_map_{i:04d}.png"
                c2 = OUTPUT_DIR / f"world_map_step_{i}.png"
                if c1.exists():
                    map_path = c1
                    st.info(f"Showing map from step {i}")
                    break
                if c2.exists():
                    map_path = c2
                    st.info(f"Showing map from step {i}")
                    break
    
    if map_path:
        image = Image.open(map_path)
        st.image(image, caption=f"World Map - Step {selected_step}", use_container_width=True)
    else:
        st.warning("No map image found for this step or recent history.")

# --- Tab 3: Analysis ---
with tab3:
    st.header("Comparative Analysis")
    
    if not selected_nations:
        subset = current_nations
        st.info("Showing all nations. Use sidebar to filter.")
    else:
        subset = current_nations[current_nations['name'].isin(selected_nations)]
    
    # Bubble Chart
    st.subheader("GDP vs Technology vs Population")
    fig_bubble = px.scatter(
        subset, 
        x="gdp", 
        y="tech", 
        size="pop", 
        color="gov", 
        hover_name="name",
        log_x=True,
        title="Nation Clusters (Size = Population)",
        height=600
    )
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    # Military Comparison
    st.subheader("Military Power Projection")
    # Melt for stacked bar
    mil_df = subset[['name', 'mil_army', 'mil_navy']].melt(id_vars='name', var_name='Branch', value_name='Power')
    fig_mil = px.bar(mil_df, x='name', y='Power', color='Branch', title="Army vs Navy Strength")
    st.plotly_chart(fig_mil, use_container_width=True)

# --- Tab 4: Networks ---
with tab4:
    st.header("Network Visualizations")
    
    # Similar logic for network images
    net_path = None
    candidate = OUTPUT_DIR / f"trade_net_{selected_step:04d}.png"
    if candidate.exists():
        net_path = candidate
    else:
        # Fallback search
        for i in range(selected_step, -1, -1):
             c = OUTPUT_DIR / f"trade_net_{i:04d}.png"
             if c.exists():
                 net_path = c
                 st.info(f"Showing network from step {i}")
                 break
    
    if net_path:
        st.image(str(net_path), caption="Trade Network Graph", use_container_width=True)
    else:
        st.warning("No network graph available.")

# --- Tab 5: Events ---
with tab5:
    st.header("Event Log")
    
    # Get raw events for this step
    # Need to find the record in raw_data matching selected_step
    step_record = next((item for item in raw_data if item["step"] == selected_step), None)
    
    if step_record and step_record.get('events'):
        events = step_record['events']
        for e in events:
            if "WAR" in e:
                st.error(f"⚔️ {e}")
            elif "CRISIS" in e:
                st.warning(f"⚠️ {e}")
            elif "ALLIANCE" in e:
                st.success(f"🤝 {e}")
            else:
                st.info(f"ℹ️ {e}")
    else:
        st.write("No major events reported this step.")
        
    st.divider()
    st.subheader("All History Search")
    
    # Searchable table of all events
    all_events = []
    for r in raw_data:
        for e in r.get('events', []):
            all_events.append({'step': r['step'], 'event': e})
            
    df_events = pd.DataFrame(all_events)
    text_search = st.text_input("Search events", "")
    
    if text_search:
        df_events = df_events[df_events['event'].str.contains(text_search, case=False)]
        
    st.dataframe(df_events, use_container_width=True)
