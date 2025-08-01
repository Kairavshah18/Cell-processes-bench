import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import numpy as np
import time
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Battery Cell Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    
    .tab-content {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if 'cells_data' not in st.session_state:
        st.session_state.cells_data = {}
    if 'tasks_data' not in st.session_state:
        st.session_state.tasks_data = {}
    if 'processes' not in st.session_state:
        st.session_state.processes = {}
    if 'simulation_data' not in st.session_state:
        st.session_state.simulation_data = {}
    if 'process_simulation_data' not in st.session_state:
        st.session_state.process_simulation_data = {}

initialize_session_state()

def create_cell_data(cell_type, idx, custom_params=None):
    """Create cell data with default or custom parameters"""
    if custom_params:
        voltage = custom_params.get('voltage', 3.2 if cell_type == "lfp" else 3.6)
        min_voltage = custom_params.get('min_voltage', 2.8 if cell_type == "lfp" else 3.2)
        max_voltage = custom_params.get('max_voltage', 3.6 if cell_type == "lfp" else 4.0)
        current = custom_params.get('current', 0.0)
        temp = custom_params.get('temp', round(random.uniform(25, 40), 1))
        capacity = custom_params.get('capacity', round(random.uniform(50, 100), 1))
    else:
        voltage = 3.2 if cell_type == "lfp" else 3.6
        min_voltage = 2.8 if cell_type == "lfp" else 3.2
        max_voltage = 3.6 if cell_type == "lfp" else 4.0
        current = 0.0
        temp = round(random.uniform(25, 40), 1)
        capacity = round(random.uniform(50, 100), 1)  # Ah capacity
    
    power_capacity = round(voltage * capacity, 2)  # Wh capacity
    
    cell_key = f"cell_{idx}_{cell_type}"
    
    return cell_key, {
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity_ah": capacity,
        "power_capacity": power_capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,
        "cell_type": cell_type,
        "soc": 80.0,  # State of charge %
        "health": 100.0  # Battery health %
    }

def simulate_single_task(cell_data, task_data, duration_minutes=10):
    """Simulate a single task execution"""
    time_points = np.linspace(0, duration_minutes, 100)
    
    voltage_data = []
    current_data = []
    temp_data = []
    soc_data = []
    
    base_voltage = cell_data['voltage']
    base_current = cell_data['current']
    base_temp = cell_data['temp']
    base_soc = cell_data['soc']
    
    for i, t in enumerate(time_points):
        # Simulate based on task type
        if task_data.get('task_type') == 'CC_CV':
            # Charging behavior
            voltage = min(cell_data['max_voltage'], 
                         base_voltage + 0.3 * (1 - np.exp(-t/5)) + random.uniform(-0.02, 0.02))
            current = max(0, 2.0 * np.exp(-t/8) + random.uniform(-0.1, 0.1))
            soc = min(100, base_soc + (t/duration_minutes) * 15 + random.uniform(-1, 1))
            
        elif task_data.get('task_type') == 'CC_CD':
            # Discharging behavior
            voltage = max(cell_data['min_voltage'], 
                         base_voltage - 0.2 * (t/duration_minutes) + random.uniform(-0.02, 0.02))
            current = abs(1.5 + 0.5 * np.sin(t/3) + random.uniform(-0.2, 0.2))
            soc = max(0, base_soc - (t/duration_minutes) * 20 + random.uniform(-1, 1))
            
        else:  # IDLE
            voltage = base_voltage + 0.01 * np.sin(t/2) + random.uniform(-0.01, 0.01)
            current = abs(0.1 + random.uniform(-0.05, 0.05))
            soc = base_soc + random.uniform(-0.5, 0.5)
        
        # Temperature simulation
        temp_change = 5 * (current / 3.0) if current > 0 else 0
        temp = base_temp + temp_change * np.sin(t/4) + random.uniform(-1, 1)
        
        voltage_data.append(max(cell_data['min_voltage'], min(cell_data['max_voltage'], voltage)))
        current_data.append(max(0, current))
        temp_data.append(max(20, min(60, temp)))
        soc_data.append(max(0, min(100, soc)))
    
    return {
        'time': time_points,
        'voltage': voltage_data,
        'current': current_data,
        'temperature': temp_data,
        'soc': soc_data
    }

def simulate_process(cells_data, process_tasks, total_duration=30):
    """Simulate entire process with multiple tasks"""
    results = {}
    
    # Calculate time allocation for each task
    total_task_time = sum([task.get('time_seconds', 3600) for task in process_tasks])
    
    for cell_key, cell_data in cells_data.items():
        combined_time = []
        combined_voltage = []
        combined_current = []
        combined_temp = []
        combined_soc = []
        
        current_time = 0
        current_cell_data = cell_data.copy()
        
        for task in process_tasks:
            task_duration = (task.get('time_seconds', 3600) / total_task_time) * total_duration
            
            # Simulate this task
            task_result = simulate_single_task(current_cell_data, task, task_duration)
            
            # Adjust time points
            adjusted_time = [t + current_time for t in task_result['time']]
            
            combined_time.extend(adjusted_time)
            combined_voltage.extend(task_result['voltage'])
            combined_current.extend(task_result['current'])
            combined_temp.extend(task_result['temperature'])
            combined_soc.extend(task_result['soc'])
            
            current_time += task_duration
            
            # Update cell state for next task
            if task_result['voltage']:
                current_cell_data['voltage'] = task_result['voltage'][-1]
                current_cell_data['temp'] = task_result['temperature'][-1]
                current_cell_data['soc'] = task_result['soc'][-1]
        
        results[cell_key] = {
            'time': combined_time,
            'voltage': combined_voltage,
            'current': combined_current,
            'temperature': combined_temp,
            'soc': combined_soc
        }
    
    return results

# Main title with custom styling
st.markdown("""
<div class="main-header">
    <h1>🔋 Advanced Battery Cell Management System</h1>
    <p>Comprehensive cell analysis, task simulation & process management</p>
</div>
""", unsafe_allow_html=True)

# Enhanced sidebar
st.sidebar.markdown("### 🚀 Navigation Panel")
tab_selection = st.sidebar.selectbox(
    "Choose Section:",
    ["🏠 Dashboard", "🔧 Cell Setup", "⚙️ Cell Customization", "📋 Task Management", 
     "🔄 Process Builder", "📊 Individual Analysis", "🎯 Task Simulation", 
     "⚡ Process Simulation", "📈 System Overview"],
    index=0
)

# Tab 1: Dashboard
if tab_selection == "🏠 Dashboard":
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🔋 Cells</h3>
            <h2>{}</h2>
        </div>
        """.format(len(st.session_state.cells_data)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📋 Tasks</h3>
            <h2>{}</h2>
        </div>
        """.format(len(st.session_state.tasks_data)), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>🔄 Processes</h3>
            <h2>{}</h2>
        </div>
        """.format(len(st.session_state.processes)), unsafe_allow_html=True)
    
    with col4:
        if st.session_state.cells_data:
            df = pd.DataFrame(st.session_state.cells_data).T
            avg_temp = df['temp'].mean()
        else:
            avg_temp = 0
        
        st.markdown("""
        <div class="metric-card">
            <h3>🌡️ Avg Temp</h3>
            <h2>{:.1f}°C</h2>
        </div>
        """.format(avg_temp), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # System status
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚡ System Status")
        if st.session_state.cells_data:
            st.success("✅ Cells configured and ready")
        else:
            st.warning("⚠️ No cells configured")
        
        if st.session_state.tasks_data:
            st.success("✅ Tasks available")
        else:
            st.info("ℹ️ No tasks defined")
        
        if st.session_state.processes:
            st.success("✅ Processes ready")
        else:
            st.info("ℹ️ No processes created")
    
    with col2:
        st.subheader("🎯 Quick Actions")
        if st.button("🔄 Reset All Data", type="secondary"):
            st.session_state.cells_data = {}
            st.session_state.tasks_data = {}
            st.session_state.processes = {}
            st.session_state.simulation_data = {}
            st.session_state.process_simulation_data = {}
            st.success("All data cleared!")
        
        if st.button("📊 Generate Sample Data", type="primary"):
            # Generate sample cells
            for i in range(3):
                cell_type = "lfp" if i % 2 == 0 else "nmc"
                cell_key, cell_data = create_cell_data(cell_type, i+1)
                st.session_state.cells_data[cell_key] = cell_data
            
            # Generate sample tasks
            sample_tasks = [
                {"task_type": "CC_CV", "cc_cp": "2A", "cv_voltage": 4.0, "current": 2.0, "capacity": 50.0, "time_seconds": 1800},
                {"task_type": "IDLE", "time_seconds": 600},
                {"task_type": "CC_CD", "cc_cp": "1.5A", "voltage": 3.0, "capacity": 40.0, "time_seconds": 2400}
            ]
            
            for i, task in enumerate(sample_tasks):
                st.session_state.tasks_data[f"task_{i+1}"] = task
            
            st.success("Sample data generated!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Tab 2: Cell Setup
elif tab_selection == "🔧 Cell Setup":
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    st.header("🔧 Cell Configuration Center")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Add New Cells")
        
        with st.form("cell_setup_form"):
            number_of_cells = st.number_input("Number of cells:", min_value=1, max_value=50, value=1)
            
            st.markdown("**Cell Configuration:**")
            cell_configs = []
            
            for i in range(min(number_of_cells, 10)):  # Limit display to 10 for UI
                st.markdown(f"**Cell {i+1}:**")
                col_a, col_b = st.columns(2)
                with col_a:
                    cell_type = st.selectbox(f"Type:", ["lfp", "nmc"], key=f"type_{i}")
                with col_b:
                    auto_params = st.checkbox(f"Auto params", value=True, key=f"auto_{i}")
                
                cell_configs.append({"type": cell_type, "auto": auto_params})
            
            submitted = st.form_submit_button("🚀 Generate Cells", type="primary")
            
            if submitted:
                st.session_state.cells_data = {}
                for i in range(number_of_cells):
                    config = cell_configs[min(i, len(cell_configs)-1)] if cell_configs else {"type": "lfp", "auto": True}
                    cell_key, cell_data = create_cell_data(config["type"], i+1)
                    st.session_state.cells_data[cell_key] = cell_data
                
                st.success(f"✅ Successfully created {number_of_cells} cells!")
    
    with col2:
        st.subheader("📋 Current Cell Inventory")
        if st.session_state.cells_data:
            # Create a clean dataframe for display
            display_data = []
            for cell_key, cell_data in st.session_state.cells_data.items():
                display_data.append({
                    "Cell ID": cell_key,
                    "Type": cell_data.get('cell_type', 'unknown'),
                    "Voltage (V)": f"{cell_data['voltage']:.2f}",
                    "Current (A)": f"{cell_data['current']:.2f}",
                    "Temperature (°C)": f"{cell_data['temp']:.1f}",
                    "Capacity (Ah)": f"{cell_data.get('capacity_ah', 0):.1f}",
                    "SoC (%)": f"{cell_data.get('soc', 0):.1f}",
                    "Health (%)": f"{cell_data.get('health', 100):.1f}"
                })
            
            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Cell type distribution
            if len(st.session_state.cells_data) > 1:
                cell_types = [cell['cell_type'] for cell in st.session_state.cells_data.values()]
                type_counts = pd.Series(cell_types).value_counts()
                
                fig = px.pie(values=type_counts.values, names=type_counts.index, 
                           title="Cell Type Distribution", hole=0.4)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🔍 No cells configured yet. Use the form on the left to add cells.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Tab 3: Cell Customization
elif tab_selection == "⚙️ Cell Customization":
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    st.header("⚙️ Advanced Cell Customization")
    
    if not st.session_state.cells_data:
        st.warning("⚠️ Please configure cells first in the Cell Setup section.")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🎯 Select & Customize")
            selected_cell = st.selectbox("Choose cell to customize:", 
                                       list(st.session_state.cells_data.keys()))
            
            if selected_cell:
                cell_data = st.session_state.cells_data[selected_cell]
                
                with st.form("customize_form"):
                    st.markdown("**⚡ Electrical Parameters**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        new_voltage = st.number_input("Voltage (V):", value=float(cell_data['voltage']), step=0.1, format="%.2f")
                        new_current = st.number_input("Current (A):", value=float(cell_data['current']), step=0.1, format="%.2f")
                        new_capacity = st.number_input("Capacity (Ah):", value=float(cell_data.get('capacity_ah', 50)), step=0.1, format="%.1f")
                    
                    with col_b:
                        new_min_voltage = st.number_input("Min Voltage (V):", value=float(cell_data['min_voltage']), step=0.1, format="%.2f")
                        new_max_voltage = st.number_input("Max Voltage (V):", value=float(cell_data['max_voltage']), step=0.1, format="%.2f")
                        new_soc = st.slider("State of Charge (%):", 0.0, 100.0, float(cell_data.get('soc', 80)), 0.1)
                    
                    st.markdown("**🌡️ Thermal Parameters**")
                    new_temp = st.number_input("Temperature (°C):", value=float(cell_data['temp']), step=0.1, format="%.1f")
                    
                    st.markdown("**🔋 Health Parameters**")
                    new_health = st.slider("Battery Health (%):", 0.0, 100.0, float(cell_data.get('health', 100)), 0.1)
                    
                    update_btn = st.form_submit_button("🔄 Update Cell", type="primary")
                    
                    if update_btn:
                        st.session_state.cells_data[selected_cell].update({
                            'voltage': new_voltage,
                            'current': new_current,
                            'temp': new_temp,
                            'capacity_ah': new_capacity,
                            'power_capacity': round(new_voltage * new_capacity, 2),
                            'min_voltage': new_min_voltage,
                            'max_voltage': new_max_voltage,
                            'soc': new_soc,
                            'health': new_health
                        })
                        st.success(f"✅ Updated {selected_cell} successfully!")
        
        with col2:
            st.subheader("📊 Current Cell Data")
            if selected_cell:
                cell_data = st.session_state.cells_data[selected_cell]
                
                # Display current values in a nice format
                st.markdown("**Current Configuration:**")
                
                # Create metrics display
                metric_col1, metric_col2 = st.columns(2)
                
                with metric_col1:
                    st.metric("Voltage", f"{cell_data['voltage']:.2f} V")
                    st.metric("Current", f"{cell_data['current']:.2f} A")
                    st.metric("Temperature", f"{cell_data['temp']:.1f} °C")
                    st.metric("SoC", f"{cell_data.get('soc', 0):.1f} %")
                
                with metric_col2:
                    st.metric("Capacity", f"{cell_data.get('capacity_ah', 0):.1f} Ah")
                    st.metric("Power Cap.", f"{cell_data.get('power_capacity', 0):.1f} Wh")
                    st.metric("Health", f"{cell_data.get('health', 100):.1f} %")
                    st.metric("Type", cell_data.get('cell_type', 'unknown').upper())
                
                # Voltage range visualization
                fig = go.Figure()
                
                # Add voltage range
                fig.add_trace(go.Bar(
                    x=['Min Voltage', 'Current Voltage', 'Max Voltage'],
                    y=[cell_data['min_voltage'], cell_data['voltage'], cell_data['max_voltage']],
                    marker_color=['red', 'blue', 'green'],
                    text=[f"{cell_data['min_voltage']:.2f}V", f"{cell_data['voltage']:.2f}V", f"{cell_data['max_voltage']:.2f}V"],
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title="Voltage Range Overview",
                    yaxis_title="Voltage (V)",
                    showlegend=False,
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Tab 4: Task Management
elif tab_selection == "📋 Task Management":
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    st.header("📋 Task Management Center")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("➕ Create New Task")
        
        with st.form("task_form"):
            task_name = st.text_input("Task Name:", value=f"Task_{len(st.session_state.tasks_data)+1}")
            task_type = st.selectbox("Task Type:", ["CC_CV", "IDLE", "CC_CD"])
            
            task_data = {"task_type": task_type, "name": task_name}
            
            if task_type == "CC_CV":
                st.markdown("**⚡ Constant Current - Constant Voltage**")
                cc_input = st.text_input("CC/CP Value:", value="2A", help="Enter value with unit (e.g., '5A' or '10W')")
                cv_voltage = st.number_input("CV Voltage (V):", value=4.0, step=0.1)
                current = st.number_input("Current (A):", value=2.0, step=0.1)
                capacity = st.number_input("Capacity:", value=50.0, step=0.1)
                time_hours = st.number_input("Time (hours):", value=1.0, step=0.1)
                
                task_data.update({
                    "cc_cp": cc_input,
                    "cv_voltage": cv_voltage,
                    "current": current,
                    "capacity": capacity,
                    "time_seconds": int(time_hours * 3600)
                })
                
            elif task_type == "IDLE":
                st.markdown("**⏸️ Idle State**")
                time_hours = st.number_input("Time (hours):", value=0.5, step=0.1)
                task_data.update({"time_seconds": int(time_hours * 3600)})
                
            elif task_type == "CC_CD":
                st.markdown("**🔋 Constant Current - Constant Discharge**")
                cc_input = st.text_input("CC/CP Value:", value="1.5A", help="Enter value with unit")
                voltage = st.number_input("Voltage (V):", value=3.0, step=0.1)
                capacity = st.number_input("Capacity:", value=40.0, step=0.1)
                time_hours = st.number_input("Time (hours):", value=1.5, step=0.1)
                
                task_data.update({
                    "cc_cp": cc_input,
                    "voltage": voltage,
                    "capacity": capacity,
                    "time_seconds": int(time_hours * 3600)
                })
            
            submitted = st.form_submit_button("🚀 Create Task", type="primary")
            
            if submitted:
                task_key = f"task_{len(st.session_state.tasks_data) + 1}"
                if task_name:
                    task_key = task_name.replace(" ", "_").lower()
                
                st.session_state.tasks_data[task_key] = task_data
                st.success(f"✅ Created task: {task_key}")
    
    with col2:
        st.subheader("📋 Task Inventory")
        if st.session_state.tasks_data:
            for task_key, task_info in st.session_state.tasks_data.items():
                with st.expander(f"🎯 {task_key.upper()}: {task_info['task_type']}", expanded=False):
                    col_a, col_b = st.columns([3, 1])
                    
                    with col_a:
                        # Display task details in a structured way
                        st.markdown(f"**Type:** {task_info['task_type']}")
                        
                        if 'time_seconds' in task_info:
                            hours = task_info['time_seconds'] / 3600
                            st.markdown(f"**Duration:** {hours:.2f} hours ({task_info['time_seconds']} seconds)")
                        
                        # Display type-specific parameters
                        for key, value in task_info.items():
                            if key not in ['task_type', 'name', 'time_seconds']:
                                st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                    
                    with col_b:
                        if st.button("🗑️ Delete", key=f"del_{task_key}", type="secondary"):
                            del st.session_state.tasks_data[task_key]
                            st.rerun()
            
            # Task type distribution
            if len(st.session_state.tasks_data) > 1:
                task_types = [task['task_type'] for task in st.session_state.tasks_data.values()]
                type_counts = pd.Series(task_types).value_counts()
                
                fig = px.bar(x=type_counts.index, y=type_counts.values,
                           title="Task Type Distribution",
                           labels={'x': 'Task Type', 'y': 'Count'})
                fig.update_traces(marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🔍 No tasks created yet. Use the form to add tasks.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Tab 5: Process Builder
elif tab_selection == "🔄 Process Builder":
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    st.header("🔄 Advanced Process Builder")
    
    if not st.session_state.tasks_data:
        st.warning("⚠️ Please create tasks first in the Task Management section.")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🏗️ Build New Process")
            
            with st.form("process_form"):
                process_name = st.text_input("Process Name:", value=f"Process_{len(st.session_state.processes)+1}")
                st.markdown("**Select Tasks for this Process:**")
                
                selected_tasks = []
                available_tasks = list(st.session_state.tasks_data.keys())
                
                for i, task_key in enumerate(available_tasks):
                    task_info = st.session_state.tasks_data[task_key]
                    include_task = st.checkbox(
                        f"{task_key} ({task_info['task_type']})", 
                        key=f"proc_task_{i}"
                    )
                    if include_task:
                        selected_tasks.append(task_key)
                
                process_description = st.text_area("Process Description:", 
                                                 placeholder="Describe what this process does...")
                
                submitted = st.form_submit_button("🚀 Create Process", type="primary")
                
                if submitted and selected_tasks:
                    process_key = process_name.replace(" ", "_").lower()
                    st.session_state.processes[
