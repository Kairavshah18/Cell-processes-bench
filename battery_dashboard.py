import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import time
import asyncio
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Battery Cell Testing Simulator",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: white;
        text-align: center;
    }
    
    .cell-status {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .task-config {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .stSelectbox > div > div {
        background-color: #2e2e2e;
    }
    
    .stNumberInput > div > div > input {
        background-color: #2e2e2e;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cells_data' not in st.session_state:
    st.session_state.cells_data = {}
if 'tasks_data' not in st.session_state:
    st.session_state.tasks_data = {}
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = pd.DataFrame()
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0

def initialize_cell(cell_type, cell_id):
    """Initialize cell parameters based on type"""
    if cell_type.lower() == "lfp":
        voltage = 3.2
        min_voltage = 2.8
        max_voltage = 3.6
    else:  # NMC
        voltage = 3.6
        min_voltage = 3.2
        max_voltage = 4.0
    
    return {
        "id": cell_id,
        "type": cell_type,
        "voltage": voltage,
        "current": 0.0,
        "temp": round(random.uniform(25, 40), 1),
        "capacity": 0.0,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,
        "current_task": "IDLE",
        "task_progress": 0
    }

def simulate_cell_step(cell_data, task_data, time_step):
    """Simulate one time step for a cell"""
    if not task_data:
        return cell_data
    
    current_task = task_data.get("task_type", "IDLE")
    cell_data["current_task"] = current_task
    
    # Simulate based on task type
    if current_task == "CC_CV":
        # Constant Current, Constant Voltage charging
        target_voltage = task_data.get("cv_voltage", cell_data["max_voltage"])
        current = task_data.get("current", 1.0)
        
        if cell_data["voltage"] < target_voltage:
            # CC phase - increase voltage
            voltage_increase = current * 0.01 + random.uniform(-0.01, 0.01)
            cell_data["voltage"] = min(cell_data["voltage"] + voltage_increase, target_voltage)
            cell_data["current"] = current + random.uniform(-0.1, 0.1)
        else:
            # CV phase - maintain voltage, decrease current
            cell_data["voltage"] = target_voltage + random.uniform(-0.02, 0.02)
            cell_data["current"] = max(0.1, cell_data["current"] - 0.05 + random.uniform(-0.02, 0.02))
    
    elif current_task == "CC_CD":
        # Constant Current Discharge
        current = -abs(task_data.get("current", 1.0))  # Negative for discharge
        target_voltage = task_data.get("voltage", cell_data["min_voltage"])
        
        voltage_decrease = abs(current) * 0.01 + random.uniform(-0.01, 0.01)
        cell_data["voltage"] = max(cell_data["voltage"] - voltage_decrease, target_voltage)
        cell_data["current"] = current + random.uniform(-0.1, 0.1)
    
    else:  # IDLE
        cell_data["current"] = random.uniform(-0.05, 0.05)
        cell_data["voltage"] += random.uniform(-0.01, 0.01)
    
    # Ensure voltage stays within limits
    cell_data["voltage"] = max(cell_data["min_voltage"], 
                              min(cell_data["max_voltage"], cell_data["voltage"]))
    
    # Update temperature (varies with current)
    temp_change = abs(cell_data["current"]) * 0.5 + random.uniform(-0.5, 0.5)
    cell_data["temp"] = max(20, min(50, cell_data["temp"] + temp_change))
    
    # Update capacity
    cell_data["capacity"] = cell_data["voltage"] * abs(cell_data["current"])
    
    return cell_data

# Sidebar Configuration
st.sidebar.title("🔋 Battery Cell Testing")
st.sidebar.markdown("---")

# Cell Configuration
st.sidebar.subheader("Cell Configuration")
num_cells = st.sidebar.number_input("Number of Cells", min_value=1, max_value=10, value=2)

# Dynamic cell type selection
for i in range(num_cells):
    cell_id = f"cell_{i+1}"
    cell_type = st.sidebar.selectbox(
        f"Cell {i+1} Type", 
        ["LFP", "NMC"], 
        key=f"cell_type_{i}"
    )
    
    if cell_id not in st.session_state.cells_data:
        st.session_state.cells_data[cell_id] = initialize_cell(cell_type, cell_id)
    else:
        st.session_state.cells_data[cell_id]["type"] = cell_type

st.sidebar.markdown("---")

# Task Configuration
st.sidebar.subheader("Task Configuration")

for cell_id in list(st.session_state.cells_data.keys())[:num_cells]:
    with st.sidebar.expander(f"Tasks for {cell_id.upper()}"):
        task_type = st.selectbox(
            "Task Type", 
            ["IDLE", "CC_CV", "CC_CD"], 
            key=f"task_type_{cell_id}"
        )
        
        task_data = {"task_type": task_type}
        
        if task_type == "CC_CV":
            st.markdown("**CC_CV Parameters:**")
            cc_value = st.number_input("CC Current (A)", value=1.0, key=f"cc_{cell_id}")
            cv_voltage = st.number_input("CV Voltage (V)", value=3.6, key=f"cv_{cell_id}")
            capacity = st.number_input("Capacity (Ah)", value=10.0, key=f"cap_{cell_id}")
            duration = st.number_input("Duration (seconds)", value=300, key=f"dur_{cell_id}")
            
            task_data.update({
                "current": cc_value,
                "cv_voltage": cv_voltage,
                "capacity": capacity,
                "duration": duration
            })
        
        elif task_type == "CC_CD":
            st.markdown("**CC_CD Parameters:**")
            cc_value = st.number_input("CC Current (A)", value=1.0, key=f"ccd_cc_{cell_id}")
            cd_voltage = st.number_input("CD Voltage (V)", value=2.8, key=f"ccd_cv_{cell_id}")
            capacity = st.number_input("Capacity (Ah)", value=10.0, key=f"ccd_cap_{cell_id}")
            duration = st.number_input("Duration (seconds)", value=300, key=f"ccd_dur_{cell_id}")
            
            task_data.update({
                "current": cc_value,
                "voltage": cd_voltage,
                "capacity": capacity,
                "duration": duration
            })
        
        elif task_type == "IDLE":
            duration = st.number_input("Duration (seconds)", value=60, key=f"idle_dur_{cell_id}")
            task_data["duration"] = duration
        
        st.session_state.tasks_data[cell_id] = task_data

st.sidebar.markdown("---")

# Control Buttons
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("▶️ Start", use_container_width=True):
        st.session_state.simulation_running = True
        st.session_state.current_time = 0
        st.session_state.simulation_data = pd.DataFrame()

with col2:
    if st.button("⏹️ Stop", use_container_width=True):
        st.session_state.simulation_running = False

# Export button
if not st.session_state.simulation_data.empty:
    csv = st.session_state.simulation_data.to_csv(index=False)
    st.sidebar.download_button(
        label="📥 Export CSV",
        data=csv,
        file_name=f"cell_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Main Area
st.title("🔋 Battery Cell Testing Simulator")

# Create columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    # Real-time Cell Overview Table
    st.subheader("📊 Live Cell Status")
    
    if st.session_state.cells_data:
        # Create DataFrame for display
        display_data = []
        for cell_id in list(st.session_state.cells_data.keys())[:num_cells]:
            cell = st.session_state.cells_data[cell_id]
            display_data.append({
                "Cell ID": cell_id.upper(),
                "Type": cell["type"],
                "Voltage (V)": f"{cell['voltage']:.2f}",
                "Current (A)": f"{cell['current']:.2f}",
                "Temp (°C)": f"{cell['temp']:.1f}",
                "Capacity (Wh)": f"{cell['capacity']:.2f}",
                "Current Task": cell["current_task"]
            })
        
        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

with col2:
    # Simulation Status
    st.subheader("🎛️ Simulation Status")
    
    status_color = "🟢" if st.session_state.simulation_running else "🔴"
    status_text = "RUNNING" if st.session_state.simulation_running else "STOPPED"
    
    st.markdown(f"""
    <div class="metric-card">
        <h3>{status_color} {status_text}</h3>
        <p>Time: {st.session_state.current_time}s</p>
        <p>Active Cells: {num_cells}</p>
    </div>
    """, unsafe_allow_html=True)

# Live Graphs
st.subheader("📈 Live Monitoring")

if not st.session_state.simulation_data.empty:
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Voltage vs Time', 'Current vs Time', 'Temperature vs Time', 'Capacity vs Time'),
        vertical_spacing=0.12
    )
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
    
    for i, cell_id in enumerate(list(st.session_state.cells_data.keys())[:num_cells]):
        cell_data = st.session_state.simulation_data[
            st.session_state.simulation_data['Cell_ID'] == cell_id
        ]
        
        if not cell_data.empty:
            color = colors[i % len(colors)]
            
            # Voltage
            fig.add_trace(
                go.Scatter(x=cell_data['Time'], y=cell_data['Voltage'], 
                          name=f'{cell_id} Voltage', line=dict(color=color)),
                row=1, col=1
            )
            
            # Current
            fig.add_trace(
                go.Scatter(x=cell_data['Time'], y=cell_data['Current'], 
                          name=f'{cell_id} Current', line=dict(color=color), showlegend=False),
                row=1, col=2
            )
            
            # Temperature
            fig.add_trace(
                go.Scatter(x=cell_data['Time'], y=cell_data['Temperature'], 
                          name=f'{cell_id} Temp', line=dict(color=color), showlegend=False),
                row=2, col=1
            )
            
            # Capacity
            fig.add_trace(
                go.Scatter(x=cell_data['Time'], y=cell_data['Capacity'], 
                          name=f'{cell_id} Capacity', line=dict(color=color), showlegend=False),
                row=2, col=2
            )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        template="plotly_dark",
        title_text="Real-time Cell Monitoring Dashboard"
    )
    
    # Update axis labels
    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
    fig.update_yaxes(title_text="Current (A)", row=1, col=2)
    fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
    fig.update_yaxes(title_text="Capacity (Wh)", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)

# Analysis Section
if not st.session_state.simulation_data.empty and not st.session_state.simulation_running:
    st.subheader("📋 Test Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Voltage Analysis**")
        voltage_stats = st.session_state.simulation_data.groupby('Cell_ID')['Voltage'].agg(['min', 'max', 'mean'])
        st.dataframe(voltage_stats.round(3))
    
    with col2:
        st.markdown("**Current Analysis**")
        current_stats = st.session_state.simulation_data.groupby('Cell_ID')['Current'].agg(['min', 'max', 'mean'])
        st.dataframe(current_stats.round(3))
    
    with col3:
        st.markdown("**Temperature Analysis**")
        temp_stats = st.session_state.simulation_data.groupby('Cell_ID')['Temperature'].agg(['min', 'max', 'mean'])
        st.dataframe(temp_stats.round(1))

# Simulation Loop
if st.session_state.simulation_running:
    placeholder = st.empty()
    
    # Simulate one time step
    st.session_state.current_time += 1
    
    # Update each cell
    new_data = []
    for cell_id in list(st.session_state.cells_data.keys())[:num_cells]:
        task_data = st.session_state.tasks_data.get(cell_id, {})
        
        # Simulate cell step
        st.session_state.cells_data[cell_id] = simulate_cell_step(
            st.session_state.cells_data[cell_id], task_data, st.session_state.current_time
        )
        
        # Record data
        cell = st.session_state.cells_data[cell_id]
        new_data.append({
            'Time': st.session_state.current_time,
            'Cell_ID': cell_id,
            'Type': cell['type'],
            'Voltage': cell['voltage'],
            'Current': cell['current'],
            'Temperature': cell['temp'],
            'Capacity': cell['capacity'],
            'Task': cell['current_task']
        })
    
    # Add to simulation data
    new_df = pd.DataFrame(new_data)
    st.session_state.simulation_data = pd.concat([st.session_state.simulation_data, new_df], ignore_index=True)
    
    # Auto-refresh every second
    time.sleep(1)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("**🔋 Battery Cell Testing Simulator** - Real-time monitoring and analysis platform")
