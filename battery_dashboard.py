import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import numpy as np
from datetime import datetime, timedelta
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import io

# Configure page
st.set_page_config(
    page_title="Battery Cell Testing Bench",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for professional dark theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2a2a2a 100%);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    .main .block-container {
        padding: 1rem 2rem;
        max-width: 100%;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1e1e1e 0%, #2d2d2d 100%);
        border-right: 2px solid #3d3d3d;
    }
    
    /* Professional cards */
    .cell-card {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        border: 1px solid #3d3d3d;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .cell-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    }
    
    /* Status indicators */
    .status-running {
        color: #4CAF50;
        font-weight: 600;
    }
    
    .status-idle {
        color: #FF9800;
        font-weight: 600;
    }
    
    .status-stopped {
        color: #F44336;
        font-weight: 600;
    }
    
    /* Enhanced buttons */
    .stButton > button {
        background: linear-gradient(145deg, #4a90e2, #357abd);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        background: linear-gradient(145deg, #357abd, #2968a3);
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(74, 144, 226, 0.4);
    }
    
    /* Form controls */
    .stSelectbox > div > div {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        border: 1px solid #3d3d3d;
        border-radius: 8px;
    }
    
    .stNumberInput > div > div > input {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        color: white;
    }
    
    /* Data tables */
    .stDataFrame {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        border-radius: 12px;
        border: 1px solid #3d3d3d;
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(135deg, #64b5f6, #42a5f5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        border-radius: 8px;
        border: 1px solid #3d3d3d;
    }
    
    /* Metrics */
    .metric-container {
        background: linear-gradient(145deg, #2a2a2a, #1e1e1e);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #3d3d3d;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    /* Progress indicators */
    .progress-bar {
        background: linear-gradient(90deg, #4CAF50, #45a049);
        height: 8px;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    /* Task status colors */
    .task-charging { color: #4CAF50; }
    .task-discharging { color: #F44336; }
    .task-idle { color: #FF9800; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'num_cells' not in st.session_state:
    st.session_state.num_cells = 2
if 'cells_config' not in st.session_state:
    st.session_state.cells_config = {}
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = pd.DataFrame()
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'simulation_paused' not in st.session_state:
    st.session_state.simulation_paused = False
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'cell_states' not in st.session_state:
    st.session_state.cell_states = {}

class BatteryCell:
    def __init__(self, cell_id, cell_type):
        self.cell_id = cell_id
        self.cell_type = cell_type
        self.tasks = []
        self.current_task_index = 0
        self.task_start_time = 0
        self.voltage = 3.2 if cell_type == "LFP" else 3.6
        self.current = 0.0
        self.is_running = False
        self.is_completed = False
        
    def add_task(self, task_type, duration):
        self.tasks.append({"type": task_type, "duration": duration})
    
    def get_voltage_range(self, task_type):
        if self.cell_type == "LFP":
            ranges = {
                "CC Charging": (3.2, 3.6),
                "Discharging": (2.8, 3.2),
                "Idle": (3.0, 3.4)
            }
        else:  # NMC
            ranges = {
                "CC Charging": (3.6, 4.2),
                "Discharging": (3.0, 3.6),
                "Idle": (3.4, 3.8)
            }
        return ranges.get(task_type, (3.0, 4.0))
    
    def get_current_range(self, task_type):
        ranges = {
            "CC Charging": (1.0, 2.0),
            "Discharging": (-1.5, -0.5),
            "Idle": (0.0, 0.0)
        }
        return ranges.get(task_type, (0.0, 0.0))
    
    def update_values(self, elapsed_time):
        if not self.tasks or self.is_completed:
            return
        
        current_task = self.tasks[self.current_task_index]
        task_elapsed = elapsed_time - self.task_start_time
        
        # Check if current task is complete
        if task_elapsed >= current_task["duration"]:
            self.current_task_index += 1
            if self.current_task_index >= len(self.tasks):
                self.is_completed = True
                self.current = 0.0
                return
            
            self.task_start_time = elapsed_time
            current_task = self.tasks[self.current_task_index]
            task_elapsed = 0
        
        # Update voltage and current based on current task
        task_type = current_task["type"]
        voltage_range = self.get_voltage_range(task_type)
        current_range = self.get_current_range(task_type)
        
        # Simulate gradual changes
        progress = min(task_elapsed / current_task["duration"], 1.0)
        
        if task_type == "CC Charging":
            self.voltage = voltage_range[0] + (voltage_range[1] - voltage_range[0]) * progress
            self.current = random.uniform(current_range[0], current_range[1])
        elif task_type == "Discharging":
            self.voltage = voltage_range[1] - (voltage_range[1] - voltage_range[0]) * progress
            self.current = random.uniform(current_range[0], current_range[1])
        else:  # Idle
            self.voltage = random.uniform(voltage_range[0], voltage_range[1])
            self.current = 0.0
    
    def get_current_task(self):
        if self.is_completed or not self.tasks:
            return "Completed", 0, 0
        
        if self.current_task_index < len(self.tasks):
            task = self.tasks[self.current_task_index]
            return task["type"], self.current_task_index + 1, len(self.tasks)
        
        return "Completed", 0, 0

def initialize_cells():
    """Initialize cells based on current configuration"""
    cells = {}
    for i in range(st.session_state.num_cells):
        cell_id = f"Cell_{i+1}"
        if cell_id in st.session_state.cells_config:
            config = st.session_state.cells_config[cell_id]
            cell = BatteryCell(cell_id, config["type"])
            for task in config.get("tasks", []):
                cell.add_task(task["type"], task["duration"])
            cells[cell_id] = cell
    return cells

def simulate_cells():
    """Run simulation for all cells"""
    cells = initialize_cells()
    data_records = []
    
    start_time = time.time()
    st.session_state.start_time = start_time
    
    while st.session_state.simulation_running:
        if st.session_state.simulation_paused:
            time.sleep(0.1)
            continue
            
        current_time = time.time()
        elapsed_time = int(current_time - start_time)
        
        # Update all cells
        all_completed = True
        for cell_id, cell in cells.items():
            if not cell.is_completed:
                all_completed = False
                cell.update_values(elapsed_time)
                
                # Record data
                data_records.append({
                    "Time": elapsed_time,
                    "Cell_ID": cell_id,
                    "Voltage": round(cell.voltage, 3),
                    "Current": round(cell.current, 3),
                    "Task": cell.get_current_task()[0]
                })
        
        # Update session state
        st.session_state.cell_states = {
            cell_id: {
                "voltage": cell.voltage,
                "current": cell.current,
                "task": cell.get_current_task()[0],
                "task_progress": f"{cell.get_current_task()[1]}/{cell.get_current_task()[2]}",
                "completed": cell.is_completed
            }
            for cell_id, cell in cells.items()
        }
        
        # Update simulation data
        if data_records:
            new_data = pd.DataFrame(data_records[-len(cells):])  # Last batch
            if st.session_state.simulation_data.empty:
                st.session_state.simulation_data = new_data
            else:
                st.session_state.simulation_data = pd.concat([st.session_state.simulation_data, new_data], ignore_index=True)
        
        # Check if all cells completed
        if all_completed:
            st.session_state.simulation_running = False
            break
            
        time.sleep(1)  # Update every second

# Header
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">
        Battery Cell Testing Bench
    </h1>
    <p style="color: #b0bec5; font-size: 1.1rem;">Real-time Battery Testing & Simulation Platform</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("## 🔧 Configuration")
    
    # Number of cells
    new_num_cells = st.selectbox(
        "Number of Cells",
        options=list(range(1, 21)),
        index=1,
        key="num_cells_selector"
    )
    
    if new_num_cells != st.session_state.num_cells:
        st.session_state.num_cells = new_num_cells
        # Reset configuration for new cell count
        st.session_state.cells_config = {}
        st.rerun()
    
    st.markdown("---")
    
    # Cell Configuration
    st.markdown("## 📱 Cell Setup")
    
    for i in range(st.session_state.num_cells):
        cell_id = f"Cell_{i+1}"
        
        with st.expander(f"🔋 {cell_id}", expanded=i == 0):
            # Cell type
            cell_type = st.selectbox(
                "Cell Type",
                ["LFP", "NMC"],
                key=f"cell_type_{i}"
            )
            
            # Initialize cell config
            if cell_id not in st.session_state.cells_config:
                st.session_state.cells_config[cell_id] = {
                    "type": cell_type,
                    "tasks": []
                }
            else:
                st.session_state.cells_config[cell_id]["type"] = cell_type
            
            # Task configuration
            st.markdown("**Task Sequence:**")
            
            # Add new task
            col1, col2 = st.columns([2, 1])
            with col1:
                task_type = st.selectbox(
                    "Task Type",
                    ["CC Charging", "Discharging", "Idle"],
                    key=f"task_type_{i}"
                )
            with col2:
                duration = st.number_input(
                    "Duration (s)",
                    min_value=1,
                    max_value=3600,
                    value=30,
                    key=f"duration_{i}"
                )
            
            if st.button(f"➕ Add Task", key=f"add_task_{i}"):
                st.session_state.cells_config[cell_id]["tasks"].append({
                    "type": task_type,
                    "duration": duration
                })
                st.rerun()
            
            # Display current tasks
            tasks = st.session_state.cells_config[cell_id].get("tasks", [])
            if tasks:
                st.markdown("**Current Tasks:**")
                for idx, task in enumerate(tasks):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        task_color = {
                            "CC Charging": "🟢",
                            "Discharging": "🔴", 
                            "Idle": "🟡"
                        }.get(task["type"], "⚪")
                        st.write(f"{task_color} {task['type']}")
                    with col2:
                        st.write(f"{task['duration']}s")
                    with col3:
                        if st.button("🗑️", key=f"delete_task_{i}_{idx}"):
                            st.session_state.cells_config[cell_id]["tasks"].pop(idx)
                            st.rerun()
    
    st.markdown("---")
    
    # Control buttons
    st.markdown("## 🎮 Controls")
    
    # Check if all cells have tasks
    all_configured = all(
        st.session_state.cells_config.get(f"Cell_{i+1}", {}).get("tasks", [])
        for i in range(st.session_state.num_cells)
    )
    
    if not st.session_state.simulation_running:
        if st.button("🚀 Start Testing", type="primary", disabled=not all_configured):
            if all_configured:
                st.session_state.simulation_running = True
                st.session_state.simulation_paused = False
                st.session_state.simulation_data = pd.DataFrame()
                st.session_state.cell_states = {}
                
                # Start simulation in thread
                thread = threading.Thread(target=simulate_cells)
                thread.daemon = True
                thread.start()
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.simulation_paused:
                if st.button("▶️ Resume"):
                    st.session_state.simulation_paused = False
                    st.rerun()
            else:
                if st.button("⏸️ Pause"):
                    st.session_state.simulation_paused = True
                    st.rerun()
        
        with col2:
            if st.button("⏹️ Stop"):
                st.session_state.simulation_running = False
                st.session_state.simulation_paused = False
                st.rerun()
    
    if not all_configured:
        st.warning("⚠️ Configure tasks for all cells before starting")

# Main Content Area
if st.session_state.simulation_running or not st.session_state.simulation_data.empty:
    
    # Real-time status
    st.markdown("## 📊 Real-time Status")
    
    if st.session_state.cell_states:
        cols = st.columns(min(len(st.session_state.cell_states), 4))
        for idx, (cell_id, state) in enumerate(st.session_state.cell_states.items()):
            with cols[idx % 4]:
                status_class = "status-running" if not state["completed"] else "status-stopped"
                st.markdown(f"""
                <div class="metric-container">
                    <h4>{cell_id}</h4>
                    <p class="{status_class}">{state["task"]}</p>
                    <p>Progress: {state["task_progress"]}</p>
                    <p>⚡ {state["voltage"]:.3f}V</p>
                    <p>🔋 {state["current"]:.3f}A</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Graphs
    if not st.session_state.simulation_data.empty:
        st.markdown("## 📈 Live Data Visualization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Voltage vs Time
            fig_voltage = px.line(
                st.session_state.simulation_data,
                x="Time",
                y="Voltage",
                color="Cell_ID",
                title="Voltage vs Time",
                labels={"Time": "Time (seconds)", "Voltage": "Voltage (V)"}
            )
            fig_voltage.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16
            )
            st.plotly_chart(fig_voltage, use_container_width=True)
        
        with col2:
            # Current vs Time
            fig_current = px.line(
                st.session_state.simulation_data,
                x="Time",
                y="Current",
                color="Cell_ID",
                title="Current vs Time",
                labels={"Time": "Time (seconds)", "Current": "Current (A)"}
            )
            fig_current.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title_font_size=16
            )
            st.plotly_chart(fig_current, use_container_width=True)
        
        # Data table
        st.markdown("## 📋 Recent Data")
        if len(st.session_state.simulation_data) > 0:
            recent_data = st.session_state.simulation_data.tail(20)
            st.dataframe(recent_data, use_container_width=True)
        
        # Export option
        if st.button("📥 Export Data to CSV"):
            if not st.session_state.simulation_data.empty:
                csv_data = st.session_state.simulation_data.to_csv(index=False)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"battery_test_data_{timestamp}.csv",
                    mime="text/csv"
                )

else:
    # Welcome screen
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <h2 style="color: #64b5f6; margin-bottom: 2rem;">Welcome to Battery Testing Bench</h2>
        <div style="background: linear-gradient(145deg, #2a2a2a, #1e1e1e); padding: 2rem; border-radius: 16px; border: 1px solid #3d3d3d;">
            <h3 style="color: #42a5f5;">Getting Started:</h3>
            <div style="text-align: left; max-width: 600px; margin: 0 auto;">
                <p>🔧 <strong>Step 1:</strong> Configure the number of cells in the sidebar</p>
                <p>📱 <strong>Step 2:</strong> Set up each cell type (LFP or NMC)</p>
                <p>⚙️ <strong>Step 3:</strong> Add task sequences for each cell</p>
                <p>🚀 <strong>Step 4:</strong> Click "Start Testing" to begin simulation</p>
            </div>
            <div style="margin-top: 2rem;">
                <p style="color: #b0bec5;"><strong>Features:</strong></p>
                <p>• Real-time voltage and current monitoring</p>
                <p>• Parallel cell simulation</p>
                <p>• Live data visualization</p>
                <p>• CSV data export</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Auto-refresh during simulation
if st.session_state.simulation_running:
    time.sleep(1)
    st.rerun()