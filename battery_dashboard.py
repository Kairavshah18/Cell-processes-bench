import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import numpy as np
import time

# Page configuration
st.set_page_config(
    page_title="Battery Cell Management System",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'cells_data' not in st.session_state:
    st.session_state.cells_data = {}
if 'tasks_data' not in st.session_state:
    st.session_state.tasks_data = {}
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = {}

def create_cell_data(cell_type, idx, custom_params=None):
    """Create cell data with default or custom parameters"""
    if custom_params:
        voltage = custom_params.get('voltage', 3.2 if cell_type == "lfp" else 3.6)
        min_voltage = custom_params.get('min_voltage', 2.8 if cell_type == "lfp" else 3.2)
        max_voltage = custom_params.get('max_voltage', 3.6 if cell_type == "lfp" else 4.0)
        current = custom_params.get('current', 0.0)
        temp = custom_params.get('temp', round(random.uniform(25, 40), 1))
    else:
        voltage = 3.2 if cell_type == "lfp" else 3.6
        min_voltage = 2.8 if cell_type == "lfp" else 3.2
        max_voltage = 3.6 if cell_type == "lfp" else 4.0
        current = 0.0
        temp = round(random.uniform(25, 40), 1)
    
    capacity = round(voltage * current, 2)
    
    cell_key = f"cell_{idx}_{cell_type}"
    
    return cell_key, {
        "voltage": voltage,
        "current": current,
        "temp": temp,
        "capacity": capacity,
        "min_voltage": min_voltage,
        "max_voltage": max_voltage,
        "cell_type": cell_type
    }

def simulate_task_execution(cells_data, task_data, duration_minutes=10):
    """Simulate task execution and generate time-series data"""
    time_points = np.linspace(0, duration_minutes, 100)
    simulation_results = {}
    
    for cell_key, cell_info in cells_data.items():
        voltage_data = []
        current_data = []
        temp_data = []
        capacity_data = []
        
        base_voltage = cell_info['voltage']
        base_current = cell_info['current']
        base_temp = cell_info['temp']
        
        for t in time_points:
            # Simulate voltage changes based on task type
            if task_data.get('task_type') == 'CC_CV':
                voltage = base_voltage + 0.1 * np.sin(t/2) + random.uniform(-0.05, 0.05)
                current = abs(base_current + 0.5 * np.cos(t/3) + random.uniform(-0.1, 0.1))
            elif task_data.get('task_type') == 'CC_CD':
                voltage = max(cell_info['min_voltage'], base_voltage - 0.02 * t + random.uniform(-0.03, 0.03))
                current = abs(base_current + 1.0 + random.uniform(-0.2, 0.2))
            else:  # IDLE
                voltage = base_voltage + random.uniform(-0.02, 0.02)
                current = abs(base_current + random.uniform(-0.05, 0.05))
            
            # Temperature simulation
            temp = base_temp + 2 * np.sin(t/5) + random.uniform(-1, 1)
            
            # Capacity calculation
            capacity = voltage * current
            
            voltage_data.append(max(cell_info['min_voltage'], min(cell_info['max_voltage'], voltage)))
            current_data.append(max(0, current))
            temp_data.append(max(20, min(50, temp)))
            capacity_data.append(capacity)
        
        simulation_results[cell_key] = {
            'time': time_points,
            'voltage': voltage_data,
            'current': current_data,
            'temperature': temp_data,
            'capacity': capacity_data
        }
    
    return simulation_results

# Main title
st.title("🔋 Battery Cell Management System")
st.markdown("---")

# Sidebar for navigation
st.sidebar.title("Navigation")
tab_selection = st.sidebar.radio(
    "Select Tab:",
    ["Cell Setup", "Cell Customization", "Task Configuration", "Cell Analysis", "Simulation Results", "System Overview"]
)

# Tab 1: Cell Setup
if tab_selection == "Cell Setup":
    st.header("🔧 Cell Setup")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Add Cells")
        number_of_cells = st.number_input("Number of cells:", min_value=1, max_value=20, value=3)
        
        if st.button("Generate Cells"):
            st.session_state.cells_data = {}
            for i in range(number_of_cells):
                cell_type = st.selectbox(f"Cell {i+1} type:", ["lfp", "nmc"], key=f"cell_type_{i}")
                cell_key, cell_data = create_cell_data(cell_type, i+1)
                st.session_state.cells_data[cell_key] = cell_data
    
    with col2:
        st.subheader("Current Cells")
        if st.session_state.cells_data:
            df = pd.DataFrame(st.session_state.cells_data).T
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No cells configured yet. Use the form on the left to add cells.")

# Tab 2: Cell Customization
elif tab_selection == "Cell Customization":
    st.header("⚙️ Cell Customization")
    
    if not st.session_state.cells_data:
        st.warning("Please set up cells first in the Cell Setup tab.")
    else:
        selected_cell = st.selectbox("Select cell to customize:", list(st.session_state.cells_data.keys()))
        
        if selected_cell:
            cell_data = st.session_state.cells_data[selected_cell]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Current Values")
                st.json(cell_data)
            
            with col2:
                st.subheader("Customize Values")
                
                new_voltage = st.number_input("Voltage (V):", value=cell_data['voltage'], step=0.1)
                new_current = st.number_input("Current (A):", value=cell_data['current'], step=0.1)
                new_temp = st.number_input("Temperature (°C):", value=cell_data['temp'], step=0.1)
                new_min_voltage = st.number_input("Min Voltage (V):", value=cell_data['min_voltage'], step=0.1)
                new_max_voltage = st.number_input("Max Voltage (V):", value=cell_data['max_voltage'], step=0.1)
                
                if st.button("Update Cell"):
                    st.session_state.cells_data[selected_cell].update({
                        'voltage': new_voltage,
                        'current': new_current,
                        'temp': new_temp,
                        'min_voltage': new_min_voltage,
                        'max_voltage': new_max_voltage,
                        'capacity': round(new_voltage * new_current, 2)
                    })
                    st.success(f"Updated {selected_cell} successfully!")

# Tab 3: Task Configuration
elif tab_selection == "Task Configuration":
    st.header("📋 Task Configuration")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Add Task")
        task_type = st.selectbox("Task Type:", ["CC_CV", "IDLE", "CC_CD"])
        
        task_data = {"task_type": task_type}
        
        if task_type == "CC_CV":
            cc_input = st.text_input("CC/CP Value (e.g., '5A' or '10W'):", value="5A")
            cv_voltage = st.number_input("CV Voltage (V):", value=4.0, step=0.1)
            current = st.number_input("Current (A):", value=1.0, step=0.1)
            capacity = st.number_input("Capacity:", value=10.0, step=0.1)
            time_seconds = st.number_input("Time (seconds):", value=3600, step=1)
            
            task_data.update({
                "cc_cp": cc_input,
                "cv_voltage": cv_voltage,
                "current": current,
                "capacity": capacity,
                "time_seconds": time_seconds
            })
            
        elif task_type == "IDLE":
            time_seconds = st.number_input("Time (seconds):", value=1800, step=1)
            task_data.update({"time_seconds": time_seconds})
            
        elif task_type == "CC_CD":
            cc_input = st.text_input("CC/CP Value (e.g., '5A' or '10W'):", value="5A")
            voltage = st.number_input("Voltage (V):", value=3.0, step=0.1)
            capacity = st.number_input("Capacity:", value=10.0, step=0.1)
            time_seconds = st.number_input("Time (seconds):", value=3600, step=1)
            
            task_data.update({
                "cc_cp": cc_input,
                "voltage": voltage,
                "capacity": capacity,
                "time_seconds": time_seconds
            })
        
        if st.button("Add Task"):
            task_key = f"task_{len(st.session_state.tasks_data) + 1}"
            st.session_state.tasks_data[task_key] = task_data
            st.success(f"Added {task_key}")
    
    with col2:
        st.subheader("Current Tasks")
        if st.session_state.tasks_data:
            for task_key, task_info in st.session_state.tasks_data.items():
                with st.expander(f"{task_key}: {task_info['task_type']}"):
                    st.json(task_info)
        else:
            st.info("No tasks configured yet.")

# Tab 4: Cell Analysis
elif tab_selection == "Cell Analysis":
    st.header("📊 Cell Analysis")
    
    if not st.session_state.cells_data:
        st.warning("Please set up cells first in the Cell Setup tab.")
    else:
        # Overall statistics
        df = pd.DataFrame(st.session_state.cells_data).T
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Cells", len(st.session_state.cells_data))
        with col2:
            st.metric("Avg Voltage", f"{df['voltage'].mean():.2f}V")
        with col3:
            st.metric("Avg Temperature", f"{df['temp'].mean():.1f}°C")
        with col4:
            st.metric("Total Capacity", f"{df['capacity'].sum():.2f}")
        
        st.markdown("---")
        
        # Individual cell analysis
        selected_cell = st.selectbox("Select cell for detailed analysis:", list(st.session_state.cells_data.keys()))
        
        if selected_cell:
            cell_data = st.session_state.cells_data[selected_cell]
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Voltage gauge
                fig_voltage = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = cell_data['voltage'],
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Voltage (V)"},
                    gauge = {
                        'axis': {'range': [None, cell_data['max_voltage']]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, cell_data['min_voltage']], 'color': "lightgray"},
                            {'range': [cell_data['min_voltage'], cell_data['max_voltage']], 'color': "gray"}],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': cell_data['max_voltage']}}))
                fig_voltage.update_layout(height=300)
                st.plotly_chart(fig_voltage, use_container_width=True)
                
                # Temperature gauge
                fig_temp = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = cell_data['temp'],
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Temperature (°C)"},
                    gauge = {
                        'axis': {'range': [None, 60]},
                        'bar': {'color': "red"},
                        'steps': [
                            {'range': [0, 25], 'color': "lightblue"},
                            {'range': [25, 40], 'color': "lightgreen"},
                            {'range': [40, 60], 'color': "orange"}],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 50}}))
                fig_temp.update_layout(height=300)
                st.plotly_chart(fig_temp, use_container_width=True)
            
            with col2:
                # Cell parameters bar chart
                params = ['voltage', 'current', 'temp', 'capacity']
                values = [cell_data[param] for param in params]
                
                fig_bar = px.bar(
                    x=params,
                    y=values,
                    title=f"{selected_cell} Parameters",
                    labels={'x': 'Parameter', 'y': 'Value'}
                )
                fig_bar.update_layout(height=300)
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Cell info table
                st.subheader("Cell Information")
                info_df = pd.DataFrame([cell_data]).T
                info_df.columns = ['Value']
                st.dataframe(info_df, use_container_width=True)

# Tab 5: Simulation Results
elif tab_selection == "Simulation Results":
    st.header("🎯 Simulation Results")
    
    if not st.session_state.cells_data or not st.session_state.tasks_data:
        st.warning("Please set up cells and tasks first.")
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Simulation Settings")
            selected_task = st.selectbox("Select task:", list(st.session_state.tasks_data.keys()))
            duration = st.slider("Simulation duration (minutes):", 1, 60, 10)
            
            if st.button("Run Simulation"):
                task_data = st.session_state.tasks_data[selected_task]
                simulation_results = simulate_task_execution(
                    st.session_state.cells_data, 
                    task_data, 
                    duration
                )
                st.session_state.simulation_data = simulation_results
                st.success("Simulation completed!")
        
        with col2:
            st.subheader("Simulation Graphs")
            
            if st.session_state.simulation_data:
                # Create subplot figure
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Voltage vs Time', 'Current vs Time', 'Temperature vs Time', 'Capacity vs Time'),
                    vertical_spacing=0.12
                )
                
                colors = px.colors.qualitative.Set1
                
                for i, (cell_key, sim_data) in enumerate(st.session_state.simulation_data.items()):
                    color = colors[i % len(colors)]
                    
                    # Voltage
                    fig.add_trace(
                        go.Scatter(x=sim_data['time'], y=sim_data['voltage'], 
                                 name=f'{cell_key} Voltage', line=dict(color=color)),
                        row=1, col=1
                    )
                    
                    # Current
                    fig.add_trace(
                        go.Scatter(x=sim_data['time'], y=sim_data['current'], 
                                 name=f'{cell_key} Current', line=dict(color=color), showlegend=False),
                        row=1, col=2
                    )
                    
                    # Temperature
                    fig.add_trace(
                        go.Scatter(x=sim_data['time'], y=sim_data['temperature'], 
                                 name=f'{cell_key} Temperature', line=dict(color=color), showlegend=False),
                        row=2, col=1
                    )
                    
                    # Capacity
                    fig.add_trace(
                        go.Scatter(x=sim_data['time'], y=sim_data['capacity'], 
                                 name=f'{cell_key} Capacity', line=dict(color=color), showlegend=False),
                        row=2, col=2
                    )
                
                fig.update_xaxes(title_text="Time (minutes)")
                fig.update_yaxes(title_text="Voltage (V)", row=1, col=1)
                fig.update_yaxes(title_text="Current (A)", row=1, col=2)
                fig.update_yaxes(title_text="Temperature (°C)", row=2, col=1)
                fig.update_yaxes(title_text="Capacity (Wh)", row=2, col=2)
                
                fig.update_layout(height=600, title_text="Battery Cell Simulation Results")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Run a simulation to see results here.")

# Tab 6: System Overview
elif tab_selection == "System Overview":
    st.header("🔍 System Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Cells Summary")
        if st.session_state.cells_data:
            df = pd.DataFrame(st.session_state.cells_data).T
            
            # Cell type distribution
            cell_types = df['cell_type'].value_counts()
            fig_pie = px.pie(values=cell_types.values, names=cell_types.index, 
                           title="Cell Type Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Voltage distribution
            fig_hist = px.histogram(df, x='voltage', title="Voltage Distribution", nbins=10)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No cells configured.")
    
    with col2:
        st.subheader("Tasks Summary")
        if st.session_state.tasks_data:
            task_types = [task['task_type'] for task in st.session_state.tasks_data.values()]
            task_counts = pd.Series(task_types).value_counts()
            
            fig_bar = px.bar(x=task_counts.index, y=task_counts.values, 
                           title="Task Type Distribution")
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tasks table
            st.subheader("Tasks Details")
            tasks_df = pd.DataFrame(st.session_state.tasks_data).T
            st.dataframe(tasks_df, use_container_width=True)
        else:
            st.info("No tasks configured.")
    
    # Combined metrics
    if st.session_state.cells_data and st.session_state.tasks_data:
        st.markdown("---")
        st.subheader("System Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        df = pd.DataFrame(st.session_state.cells_data).T
        
        with col1:
            st.metric("Total Cells", len(st.session_state.cells_data))
        with col2:
            st.metric("Total Tasks", len(st.session_state.tasks_data))
        with col3:
            st.metric("System Voltage", f"{df['voltage'].sum():.2f}V")
        with col4:
            st.metric("System Capacity", f"{df['capacity'].sum():.2f}Wh")

# Footer
st.markdown("---")
st.markdown("**Battery Cell Management System** - Built with Streamlit")
