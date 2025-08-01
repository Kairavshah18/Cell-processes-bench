import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import random
from datetime import datetime, timedelta
import json
from io import StringIO
import threading

# Page configuration
st.set_page_config(
    page_title="Battery Cell Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }
    
    .status-running {
        color: #10b981;
        font-weight: 600;
    }
    
    .status-idle {
        color: #f59e0b;
        font-weight: 600;
    }
    
    .status-stopped {
        color: #ef4444;
        font-weight: 600;
    }
    
    .task-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'cells_data' not in st.session_state:
        st.session_state.cells_data = {}
    if 'tasks_data' not in st.session_state:
        st.session_state.tasks_data = {}
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    if 'simulation_data' not in st.session_state:
        st.session_state.simulation_data = []
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'current_time' not in st.session_state:
        st.session_state.current_time = 0
    if 'total_simulation_time' not in st.session_state:
        st.session_state.total_simulation_time = 0
    if 'simulation_completed' not in st.session_state:
        st.session_state.simulation_completed = False

# Cell management functions
def randomize_cell_data(cell_type):
    """Generate random data for a cell based on its type"""
    if cell_type.lower() == "lfp":
        voltage = round(random.uniform(3.0, 3.4), 2)
        min_voltage = 2.8
        max_voltage = 3.6
    else:  # li-ion or other
        voltage = round(random.uniform(3.4, 3.8), 2)
        min_voltage = 3.2
        max_voltage = 4.0
    
    current = round(random.uniform(0, 5), 2)
    temp = round(random.uniform(25, 40), 1)
    capacity = round(voltage * current, 2)
    
    return {
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity": capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage
    }

def simulate_task_execution(cell_key, task_data, elapsed_time):
    """Simulate task execution and update cell parameters"""
    cell_data = st.session_state.cells_data[cell_key].copy()
    task_type = task_data.get("task_type", "IDLE")
    
    if task_type == "CC_CV":
        # Constant Current - Constant Voltage charging simulation
        if elapsed_time < task_data.get("time_seconds", 0) / 2:
            # CC phase
            cell_data["current"] = task_data.get("current", 0)
            cell_data["voltage"] = min(cell_data["voltage"] + 0.001 * elapsed_time, 
                                     task_data.get("cv_voltage", cell_data["max_voltage"]))
        else:
            # CV phase
            cell_data["voltage"] = task_data.get("cv_voltage", cell_data["max_voltage"])
            cell_data["current"] = max(task_data.get("current", 0) * 0.95, 0.1)
        
        cell_data["temp"] = min(cell_data["temp"] + random.uniform(-0.1, 0.3), 50)
        
    elif task_type == "CC_CD":
        # Constant Current - Constant Discharge simulation
        cell_data["current"] = -abs(task_data.get("current", 0))  # Negative for discharge
        cell_data["voltage"] = max(cell_data["voltage"] - 0.0005 * elapsed_time, 
                                 cell_data["min_voltage"])
        cell_data["temp"] = min(cell_data["temp"] + random.uniform(-0.05, 0.2), 45)
        
    elif task_type == "IDLE":
        # Idle state - minimal changes
        cell_data["current"] = 0
        cell_data["temp"] = max(cell_data["temp"] - 0.05, 25)
    
    cell_data["capacity"] = abs(cell_data["voltage"] * cell_data["current"])
    return cell_data

# Main application
def main():
    initialize_session_state()
    
    st.markdown('<h1 class="main-header">🔋 Battery Cell Management System</h1>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### Navigation")
        tab_selection = st.selectbox(
            "Select Section",
            ["Cell Configuration", "Task Management", "Real-time Simulation", "Data Analysis", "Export Data"],
            index=0
        )
        
        st.markdown("---")
        st.markdown("### System Status")
        if st.session_state.simulation_running:
            st.markdown('<p class="status-running">● RUNNING</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-idle">● IDLE</p>', unsafe_allow_html=True)
        
        if st.session_state.cells_data:
            st.metric("Total Cells", len(st.session_state.cells_data))
        
        if st.session_state.simulation_running and st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            st.metric("Runtime", f"{elapsed:.1f}s")

    # Tab content based on selection
    if tab_selection == "Cell Configuration":
        cell_configuration_tab()
    elif tab_selection == "Task Management":
        task_management_tab()
    elif tab_selection == "Real-time Simulation":
        simulation_tab()
    elif tab_selection == "Data Analysis":
        analysis_tab()
    elif tab_selection == "Export Data":
        export_tab()

def cell_configuration_tab():
    st.header("Cell Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Add New Cells")
        
        # Number of cells input
        num_cells = st.number_input("Number of cells to add", min_value=1, max_value=20, value=1)
        
        # Quick add with random data
        st.subheader("Quick Add with Random Data")
        with st.form("quick_add_form"):
            cell_types_quick = []
            for i in range(num_cells):
                cell_type = st.selectbox(f"Cell {i+1} Type", ["LFP", "Li-ion", "NMC", "LTO"], key=f"quick_type_{i}")
                cell_types_quick.append(cell_type)
            
            if st.form_submit_button("Add Cells with Random Data", use_container_width=True):
                for i, cell_type in enumerate(cell_types_quick):
                    cell_key = f"cell_{len(st.session_state.cells_data)+1}_{cell_type.lower()}"
                    random_data = randomize_cell_data(cell_type)
                    
                    # Set voltage limits based on cell type
                    if cell_type.lower() == "lfp":
                        min_voltage, max_voltage = 2.8, 3.6
                    else:
                        min_voltage, max_voltage = 3.2, 4.0
                    
                    st.session_state.cells_data[cell_key] = {
                        "type": cell_type,
                        "voltage": random_data["voltage"],
                        "current": random_data["current"],
                        "temp": random_data["temp"],
                        "capacity": random_data["capacity"],
                        "min_voltage": min_voltage,
                        "max_voltage": max_voltage
                    }
                
                st.success(f"Added {len(cell_types_quick)} cells with random data!")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Manual Cell Configuration")
        
        # Cell configuration form
        with st.form("cell_config_form"):
            cells_to_add = []
            
            for i in range(num_cells):
                st.markdown(f"**Cell {i+1} Configuration**")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    cell_type = st.selectbox(f"Cell {i+1} Type", ["LFP", "Li-ion", "NMC", "LTO"], key=f"type_{i}")
                    voltage = st.number_input(f"Initial Voltage (V)", min_value=0.0, max_value=5.0, value=3.2, step=0.1, key=f"voltage_{i}")
                    current = st.number_input(f"Initial Current (A)", min_value=0.0, max_value=10.0, value=0.0, step=0.1, key=f"current_{i}")
                
                with col_b:
                    temp = st.number_input(f"Temperature (°C)", min_value=0.0, max_value=80.0, value=25.0, step=0.1, key=f"temp_{i}")
                    capacity = st.number_input(f"Capacity (Wh)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"capacity_{i}")
                
                cells_to_add.append({
                    "type": cell_type,
                    "voltage": voltage,
                    "current": current,
                    "temp": temp,
                    "capacity": capacity
                })
                
                st.markdown("---")
            
            if st.form_submit_button("Add Cells Manually", use_container_width=True):
                for i, cell_config in enumerate(cells_to_add):
                    cell_key = f"cell_{len(st.session_state.cells_data)+1}_{cell_config['type'].lower()}"
                    
                    # Set voltage limits based on cell type
                    if cell_config['type'].lower() == "lfp":
                        min_voltage, max_voltage = 2.8, 3.6
                    else:
                        min_voltage, max_voltage = 3.2, 4.0
                    
                    st.session_state.cells_data[cell_key] = {
                        "type": cell_config['type'],
                        "voltage": cell_config['voltage'],
                        "current": cell_config['current'],
                        "temp": cell_config['temp'],
                        "capacity": cell_config['capacity'],
                        "min_voltage": min_voltage,
                        "max_voltage": max_voltage
                    }
                
                st.success(f"Added {len(cells_to_add)} cells successfully!")
                st.rerun()
    
    with col2:
        st.subheader("Current Cells")
        
        if st.session_state.cells_data:
            for cell_key, cell_data in st.session_state.cells_data.items():
                with st.container():
                    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
                    st.markdown(f"**{cell_key.upper()}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Voltage", f"{cell_data['voltage']:.2f}V")
                        st.metric("Current", f"{cell_data['current']:.2f}A")
                    with col_b:
                        st.metric("Temperature", f"{cell_data['temp']:.1f}°C")
                        st.metric("Capacity", f"{cell_data['capacity']:.2f}Wh")
                    
                    if st.button(f"Randomize {cell_key}", key=f"rand_{cell_key}"):
                        random_data = randomize_cell_data(cell_data.get('type', 'li-ion'))
                        st.session_state.cells_data[cell_key].update(random_data)
                        st.rerun()
                    
                    if st.button(f"Remove {cell_key}", key=f"remove_{cell_key}"):
                        del st.session_state.cells_data[cell_key]
                        if cell_key in st.session_state.tasks_data:
                            del st.session_state.tasks_data[cell_key]
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info("No cells configured yet. Add some cells to get started!")

def task_management_tab():
    st.header("Task Management")
    
    if not st.session_state.cells_data:
        st.warning("Please configure cells first before adding tasks.")
        return
    
    # Select cell for task management
    selected_cell = st.selectbox("Select Cell for Task Management", list(st.session_state.cells_data.keys()))
    
    if selected_cell not in st.session_state.tasks_data:
        st.session_state.tasks_data[selected_cell] = []
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Add Task for {selected_cell}")
        
        with st.form("task_form"):
            task_type = st.selectbox("Task Type", ["CC_CV", "CC_CD", "IDLE"])
            
            if task_type == "CC_CV":
                st.markdown("**Constant Current - Constant Voltage (Charging)**")
                cc_input = st.text_input("CC Value (e.g., '5A' or '10W')", value="2A")
                cv_voltage = st.number_input("CV Voltage (V)", min_value=0.0, max_value=5.0, value=4.0, step=0.1)
                current = st.number_input("Current (A)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
                capacity = st.number_input("Target Capacity", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
                time_seconds = st.number_input("Time (seconds)", min_value=1, max_value=7200, value=300)
                
                task_data = {
                    "task_type": "CC_CV",
                    "cc_cp": cc_input,
                    "cv_voltage": cv_voltage,
                    "current": current,
                    "capacity": capacity,
                    "time_seconds": time_seconds
                }
                
            elif task_type == "CC_CD":
                st.markdown("**Constant Current - Constant Discharge**")
                cc_input = st.text_input("CC Value (e.g., '3A' or '8W')", value="1A")
                voltage = st.number_input("Cutoff Voltage (V)", min_value=0.0, max_value=5.0, value=3.0, step=0.1)
                capacity = st.number_input("Target Capacity", min_value=0.0, max_value=100.0, value=8.0, step=0.1)
                time_seconds = st.number_input("Time (seconds)", min_value=1, max_value=7200, value=600)
                
                task_data = {
                    "task_type": "CC_CD",
                    "cc_cp": cc_input,
                    "voltage": voltage,
                    "capacity": capacity,
                    "time_seconds": time_seconds
                }
                
            else:  # IDLE
                st.markdown("**Idle State**")
                time_seconds = st.number_input("Time (seconds)", min_value=1, max_value=7200, value=120)
                
                task_data = {
                    "task_type": "IDLE",
                    "time_seconds": time_seconds
                }
            
            if st.form_submit_button("Add Task"):
                st.session_state.tasks_data[selected_cell].append(task_data)
                st.success("Task added successfully!")
                st.rerun()
    
    with col2:
        st.subheader(f"Tasks for {selected_cell}")
        
        if st.session_state.tasks_data[selected_cell]:
            for i, task in enumerate(st.session_state.tasks_data[selected_cell]):
                with st.container():
                    st.markdown(f'<div class="task-card">', unsafe_allow_html=True)
                    st.markdown(f"**Task {i+1}: {task['task_type']}**")
                    st.markdown(f"Duration: {task['time_seconds']}s")
                    
                    if task['task_type'] == "CC_CV":
                        st.markdown(f"CC: {task['cc_cp']}, CV: {task['cv_voltage']}V")
                    elif task['task_type'] == "CC_CD":
                        st.markdown(f"CC: {task['cc_cp']}, Cutoff: {task['voltage']}V")
                    
                    if st.button(f"Remove Task {i+1}", key=f"remove_task_{selected_cell}_{i}"):
                        st.session_state.tasks_data[selected_cell].pop(i)
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No tasks added yet for this cell.")
    
    # Display all tasks summary
    st.subheader("All Tasks Summary")
    if any(st.session_state.tasks_data.values()):
        for cell_key, tasks in st.session_state.tasks_data.items():
            if tasks:
                st.markdown(f"**{cell_key}**: {len(tasks)} tasks, Total time: {sum(task['time_seconds'] for task in tasks)}s")
    else:
        st.info("No tasks configured for any cells.")

def simulation_tab():
    st.header("Real-time Simulation")
    
    if not st.session_state.cells_data:
        st.warning("Please configure cells first.")
        return
    
    if not any(st.session_state.tasks_data.values()):
        st.warning("Please add tasks to cells before starting simulation.")
        return
    
    # Calculate total simulation time
    total_time = 0
    for cell_key, tasks in st.session_state.tasks_data.items():
        if tasks:
            cell_total_time = sum(task['time_seconds'] for task in tasks)
            total_time = max(total_time, cell_total_time)
    
    st.session_state.total_simulation_time = total_time
    
    # Display simulation info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Simulation Time", f"{total_time}s")
    
    with col2:
        if st.session_state.simulation_running and st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            remaining = max(0, total_time - elapsed)
            st.metric("Time Remaining", f"{remaining:.1f}s")
        else:
            st.metric("Time Remaining", f"{total_time}s")
    
    with col3:
        if st.session_state.simulation_running and st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            progress = min(elapsed / total_time * 100, 100) if total_time > 0 else 0
            st.metric("Progress", f"{progress:.1f}%")
        else:
            st.metric("Progress", "0%")
    
    with col4:
        if st.session_state.simulation_completed:
            st.metric("Status", "✅ Completed")
        elif st.session_state.simulation_running:
            st.metric("Status", "🔄 Running")
        else:
            st.metric("Status", "⏸️ Stopped")
    
    # Progress bar
    if st.session_state.simulation_running and st.session_state.start_time:
        elapsed = time.time() - st.session_state.start_time
        progress = min(elapsed / total_time, 1.0) if total_time > 0 else 0
        st.progress(progress)
    else:
        st.progress(0)
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Simulation", disabled=st.session_state.simulation_running):
            st.session_state.simulation_running = True
            st.session_state.start_time = time.time()
            st.session_state.simulation_data = []
            st.session_state.simulation_completed = False
            st.rerun()
    
    with col2:
        if st.button("Stop Simulation", disabled=not st.session_state.simulation_running):
            st.session_state.simulation_running = False
            st.session_state.simulation_completed = False
            st.rerun()
    
    with col3:
        if st.button("Reset Data"):
            st.session_state.simulation_data = []
            st.session_state.simulation_running = False
            st.session_state.start_time = None
            st.session_state.simulation_completed = False
            st.rerun()
    
    # Real-time display
    if st.session_state.simulation_running:
        # Create placeholders for real-time updates
        status_placeholder = st.empty()
        metrics_placeholder = st.empty()
        chart_placeholder = st.empty()
        
        # Simulation loop
        current_time = time.time()
        elapsed = current_time - st.session_state.start_time if st.session_state.start_time else 0
        
        # Check if simulation should stop automatically
        if elapsed >= total_time:
            st.session_state.simulation_running = False
            st.session_state.simulation_completed = True
            st.success("🎉 Simulation completed successfully!")
            st.rerun()
        
        # Update cell data based on current tasks
        updated_cells = {}
        active_cells = 0
        
        for cell_key, tasks in st.session_state.tasks_data.items():
            if tasks and cell_key in st.session_state.cells_data:
                # Find current task based on elapsed time
                cumulative_time = 0
                current_task = None
                task_elapsed = 0
                task_index = -1
                
                for i, task in enumerate(tasks):
                    if elapsed >= cumulative_time and elapsed < cumulative_time + task['time_seconds']:
                        current_task = task
                        task_elapsed = elapsed - cumulative_time
                        task_index = i
                        active_cells += 1
                        break
                    cumulative_time += task['time_seconds']
                
                if current_task:
                    updated_cell_data = simulate_task_execution(cell_key, current_task, task_elapsed)
                    updated_cells[cell_key] = {
                        **updated_cell_data,
                        'current_task': current_task['task_type'],
                        'task_index': task_index + 1,
                        'task_progress': (task_elapsed / current_task['time_seconds']) * 100
                    }
                    st.session_state.cells_data[cell_key] = updated_cell_data
                else:
                    # Cell has finished all tasks
                    updated_cells[cell_key] = {
                        **st.session_state.cells_data[cell_key],
                        'current_task': 'COMPLETED',
                        'task_index': len(tasks),
                        'task_progress': 100
                    }
        
        # Store simulation data
        if updated_cells:
            data_point = {
                'timestamp': current_time,
                'elapsed': elapsed,
                **{f"{cell_key}_{param}": value for cell_key, cell_data in updated_cells.items() 
                   for param, value in cell_data.items() if isinstance(value, (int, float)) and not param.startswith('task')}
            }
            st.session_state.simulation_data.append(data_point)
        
        # Update displays
        with status_placeholder:
            if active_cells > 0:
                st.info(f"⚡ Simulation Running - {active_cells} active cells - Elapsed: {elapsed:.1f}s / {total_time}s")
            else:
                st.warning(f"⏳ All cells completed - Elapsed: {elapsed:.1f}s / {total_time}s")
        
        with metrics_placeholder:
            if updated_cells:
                cols = st.columns(len(updated_cells))
                for i, (cell_key, cell_data) in enumerate(updated_cells.items()):
                    with cols[i]:
                        st.markdown(f"**{cell_key}**")
                        
                        # Current task info
                        task_status = cell_data.get('current_task', 'IDLE')
                        task_num = cell_data.get('task_index', 0)
                        task_progress = cell_data.get('task_progress', 0)
                        
                        if task_status == 'COMPLETED':
                            st.success(f"✅ All Tasks Done")
                        else:
                            st.info(f"🔄 Task {task_num}: {task_status}")
                            st.progress(task_progress / 100)
                        
                        # Cell metrics
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Voltage", f"{cell_data['voltage']:.3f}V")
                            st.metric("Current", f"{cell_data['current']:.3f}A")
                        with col_b:
                            st.metric("Temp", f"{cell_data['temp']:.1f}°C")
                            st.metric("Capacity", f"{cell_data['capacity']:.3f}Wh")
        
        # Real-time chart
        with chart_placeholder:
            if len(st.session_state.simulation_data) > 1:
                df = pd.DataFrame(st.session_state.simulation_data)
                
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Voltage vs Time', 'Current vs Time', 'Temperature vs Time', 'Capacity vs Time'),
                    vertical_spacing=0.08
                )
                
                colors = px.colors.qualitative.Set1
                
                for i, cell_key in enumerate([k for k in updated_cells.keys()]):
                    color = colors[i % len(colors)]
                    
                    # Voltage
                    voltage_col = f'{cell_key}_voltage'
                    if voltage_col in df.columns:
                        fig.add_trace(
                            go.Scatter(x=df['elapsed'], y=df[voltage_col], 
                                     name=f'{cell_key} Voltage', line=dict(color=color)),
                            row=1, col=1
                        )
                    
                    # Current
                    current_col = f'{cell_key}_current'
                    if current_col in df.columns:
                        fig.add_trace(
                            go.Scatter(x=df['elapsed'], y=df[current_col], 
                                     name=f'{cell_key} Current', line=dict(color=color)),
                            row=1, col=2
                        )
                    
                    # Temperature
                    temp_col = f'{cell_key}_temp'
                    if temp_col in df.columns:
                        fig.add_trace(
                            go.Scatter(x=df['elapsed'], y=df[temp_col], 
                                     name=f'{cell_key} Temp', line=dict(color=color)),
                            row=2, col=1
                        )
                    
                    # Capacity
                    capacity_col = f'{cell_key}_capacity'
                    if capacity_col in df.columns:
                        fig.add_trace(
                            go.Scatter(x=df['elapsed'], y=df[capacity_col], 
                                     name=f'{cell_key} Capacity', line=dict(color=color)),
                            row=2, col=2
                        )
                
                fig.update_layout(height=600, showlegend=False, title_text="Real-time Cell Parameters")
                fig.update_xaxes(title_text="Time (s)")
                fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
                fig.update_yaxes(title_text="Current (A)", row=1, col=2)
                fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
                fig.update_yaxes(title_text="Capacity (Wh)", row=2, col=2)
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Auto-refresh every second
        time.sleep(1)
        st.rerun()
    
    elif st.session_state.simulation_completed:
        st.success("🎉 Simulation completed successfully!")
        st.info(f"Total simulation time: {total_time}s")
        
        if st.session_state.simulation_data:
            st.info(f"Collected {len(st.session_state.simulation_data)} data points. Go to 'Data Analysis' tab to view results.")
    
    else:
        st.info("Click 'Start Simulation' to begin real-time monitoring.")
        
        # Show task summary when not running
        st.subheader("Simulation Overview")
        for cell_key, tasks in st.session_state.tasks_data.items():
            if tasks:
                with st.expander(f"{cell_key} - {len(tasks)} tasks ({sum(task['time_seconds'] for task in tasks)}s total)"):
                    for i, task in enumerate(tasks):
                        st.markdown(f"**Task {i+1}**: {task['task_type']} - {task['time_seconds']}s")
                        if task['task_type'] == 'CC_CV':
                            st.markdown(f"  - CC: {task.get('cc_cp', 'N/A')}, CV: {task.get('cv_voltage', 0):.2f}V")
                        elif task['task_type'] == 'CC_CD':
                            st.markdown(f"  - CC: {task.get('cc_cp', 'N/A')}, Cutoff: {task.get('voltage', 0):.2f}V")

def analysis_tab():
    st.header("Data Analysis")
    
    if not st.session_state.simulation_data:
        st.info("No simulation data available. Run a simulation first to see analysis.")
        return
    
    df = pd.DataFrame(st.session_state.simulation_data)
    
    # Summary statistics
    st.subheader("Summary Statistics")
    
    # Get cell names from dataframe columns
    cell_columns = [col for col in df.columns if col not in ['timestamp', 'elapsed']]
    cell_names = list(set([col.split('_')[0] + '_' + col.split('_')[1] + '_' + col.split('_')[2] for col in cell_columns]))
    
    if cell_names:
        selected_cell = st.selectbox("Select Cell for Detailed Analysis", cell_names)
        
        # Filter data for selected cell
        cell_data_cols = [col for col in df.columns if col.startswith(selected_cell)]
        
        if cell_data_cols:
            # Create comprehensive analysis charts
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    'Voltage Over Time', 'Current Over Time',
                    'Temperature Over Time', 'Capacity Over Time',
                    'Voltage Distribution', 'Current Distribution'
                ),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Time series plots
            voltage_col = f"{selected_cell}_voltage"
            current_col = f"{selected_cell}_current"
            temp_col = f"{selected_cell}_temp"
            capacity_col = f"{selected_cell}_capacity"
            
            if voltage_col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['elapsed'], y=df[voltage_col], name='Voltage', line=dict(color='blue')),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Histogram(x=df[voltage_col], name='Voltage Dist', marker_color='blue', opacity=0.7),
                    row=3, col=1
                )
            
            if current_col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['elapsed'], y=df[current_col], name='Current', line=dict(color='red')),
                    row=1, col=2
                )
                fig.add_trace(
                    go.Histogram(x=df[current_col], name='Current Dist', marker_color='red', opacity=0.7),
                    row=3, col=2
                )
            
            if temp_col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['elapsed'], y=df[temp_col], name='Temperature', line=dict(color='orange')),
                    row=2, col=1
                )
            
            if capacity_col in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['elapsed'], y=df[capacity_col], name='Capacity', line=dict(color='green')),
                    row=2, col=2
                )
            
            fig.update_layout(height=800, showlegend=False, title_text=f"Comprehensive Analysis - {selected_cell}")
            fig.update_xaxes(title_text="Time (s)")
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Statistical summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Statistical Summary")
                summary_data = {}
                
                for param in ['voltage', 'current', 'temp', 'capacity']:
                    col_name = f"{selected_cell}_{param}"
                    if col_name in df.columns:
                        summary_data[param.title()] = {
                            'Mean': f"{df[col_name].mean():.3f}",
                            'Std': f"{df[col_name].std():.3f}",
                            'Min': f"{df[col_name].min():.3f}",
                            'Max': f"{df[col_name].max():.3f}"
                        }
                
                summary_df = pd.DataFrame(summary_data).T
                st.dataframe(summary_df, use_container_width=True)
            
            with col2:
                st.subheader("Performance Metrics")
                
                if voltage_col in df.columns and current_col in df.columns:
                    # Calculate energy metrics
                    avg_power = (df[voltage_col] * df[current_col]).mean()
                    total_energy = (df[voltage_col] * df[current_col] * df['elapsed'].diff().fillna(1)).sum()
                    efficiency = (df[voltage_col] / df[voltage_col].max() * 100).mean()
                    
                    metrics_data = {
                        'Average Power': f"{avg_power:.3f} W",
                        'Total Energy': f"{total_energy:.3f} Wh",
                        'Avg Efficiency': f"{efficiency:.1f}%",
                        'Runtime': f"{df['elapsed'].max():.1f} s"
                    }
                    
                    for metric, value in metrics_data.items():
                        st.metric(metric, value)
    
    # Comparison analysis
    if len(cell_names) > 1:
        st.subheader("Cell Comparison")
        
        comparison_param = st.selectbox("Parameter to Compare", ['voltage', 'current', 'temp', 'capacity'])
        
        fig = go.Figure()
        
        for cell_name in cell_names:
            col_name = f"{cell_name}_{comparison_param}"
            if col_name in df.columns:
                fig.add_trace(
                    go.Scatter(x=df['elapsed'], y=df[col_name], 
                             name=f"{cell_name} {comparison_param.title()}", 
                             mode='lines')
                )
        
        fig.update_layout(
            title=f"{comparison_param.title()} Comparison Across All Cells",
            xaxis_title="Time (s)",
            yaxis_title=f"{comparison_param.title()}",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Bar chart comparison of final values
        final_values = {}
        for cell_name in cell_names:
            col_name = f"{cell_name}_{comparison_param}"
            if col_name in df.columns:
                final_values[cell_name] = df[col_name].iloc[-1]
        
        if final_values:
            fig_bar = go.Figure(data=[
                go.Bar(x=list(final_values.keys()), y=list(final_values.values()),
                       marker_color='lightblue', text=[f"{v:.3f}" for v in final_values.values()],
                       textposition='auto')
            ])
            
            fig_bar.update_layout(
                title=f"Final {comparison_param.title()} Values",
                xaxis_title="Cells",
                yaxis_title=f"{comparison_param.title()}",
                height=400
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)

def export_tab():
    st.header("Export Data")
    
    if not st.session_state.simulation_data:
        st.info("No simulation data available for export. Run a simulation first.")
        return
    
    df = pd.DataFrame(st.session_state.simulation_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
        
        st.markdown(f"**Total Records:** {len(df)}")
        st.markdown(f"**Columns:** {len(df.columns)}")
        st.markdown(f"**Duration:** {df['elapsed'].max():.1f} seconds")
    
    with col2:
        st.subheader("Export Options")
        
        # Export format selection
        export_format = st.selectbox("Select Export Format", ["CSV", "JSON", "Excel"])
        
        # Date range filter
        st.markdown("**Filter Options:**")
        
        if len(df) > 0:
            min_time = df['elapsed'].min()
            max_time = df['elapsed'].max()
            
            time_range = st.slider(
                "Time Range (seconds)",
                min_value=float(min_time),
                max_value=float(max_time),
                value=(float(min_time), float(max_time)),
                step=1.0
            )
            
            # Filter dataframe based on time range
            filtered_df = df[(df['elapsed'] >= time_range[0]) & (df['elapsed'] <= time_range[1])]
            
            # Column selection
            all_columns = df.columns.tolist()
            selected_columns = st.multiselect(
                "Select Columns to Export",
                all_columns,
                default=all_columns
            )
            
            if selected_columns:
                export_df = filtered_df[selected_columns]
                
                # Generate export data
                if export_format == "CSV":
                    csv_data = export_df.to_csv(index=False)
                    file_name = f"battery_simulation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=file_name,
                        mime="text/csv",
                        use_container_width=True
                    )
                
                elif export_format == "JSON":
                    json_data = export_df.to_json(orient='records', indent=2)
                    file_name = f"battery_simulation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=file_name,
                        mime="application/json",
                        use_container_width=True
                    )
                
                elif export_format == "Excel":
                    try:
                        # Create Excel file in memory
                        from io import BytesIO
                        excel_buffer = BytesIO()
                        
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            export_df.to_excel(writer, sheet_name='Simulation_Data', index=False)
                            
                            # Add summary sheet
                            summary_data = {
                                'Metric': ['Total Records', 'Duration (s)', 'Start Time', 'Export Time'],
                                'Value': [
                                    len(export_df),
                                    f"{export_df['elapsed'].max():.1f}",
                                    datetime.fromtimestamp(export_df['timestamp'].min()).strftime('%Y-%m-%d %H:%M:%S'),
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                ]
                            }
                            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                        
                        excel_data = excel_buffer.getvalue()
                        file_name = f"battery_simulation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        st.download_button(
                            label="Download Excel",
                            data=excel_data,
                            file_name=file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except ImportError:
                        st.error("Excel export requires openpyxl. Please install it with: pip install openpyxl")
                    except Exception as e:
                        st.error(f"Error creating Excel file: {str(e)}")
                
                st.success(f"Export ready! Filtered data contains {len(export_df)} records.")
        
        # Export configuration data
        st.markdown("---")
        st.subheader("Export Configuration")
        
        if st.button("Export Cell Configuration", use_container_width=True):
            config_data = {
                'cells': st.session_state.cells_data,
                'tasks': st.session_state.tasks_data,
                'export_time': datetime.now().isoformat()
            }
            
            config_json = json.dumps(config_data, indent=2)
            file_name = f"battery_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            st.download_button(
                label="Download Configuration JSON",
                data=config_json,
                file_name=file_name,
                mime="application/json",
                use_container_width=True
            )
        
        # Import configuration
        st.markdown("**Import Configuration:**")
        uploaded_config = st.file_uploader("Upload Configuration File", type=['json'])
        
        if uploaded_config is not None:
            try:
                config_data = json.loads(uploaded_config.read())
                
                if st.button("Load Configuration"):
                    if 'cells' in config_data:
                        st.session_state.cells_data = config_data['cells']
                    if 'tasks' in config_data:
                        st.session_state.tasks_data = config_data['tasks']
                    
                    st.success("Configuration loaded successfully!")
                    st.rerun()
                    
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid configuration file.")

if __name__ == "__main__":
    main()
