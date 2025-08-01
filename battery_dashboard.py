import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
from datetime import datetime
import random

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(page_title="Battery Cell Testing Bench", layout="wide")

# --------------------------
# SIDEBAR: CONFIGURATION
# --------------------------
st.sidebar.header("⚙️ Configuration")

# Number of cells
num_cells = st.sidebar.number_input("Number of Cells", min_value=1, value=3, step=1)

# Cell data dictionary
cell_data = {}
cell_types = {}

# Randomize values function
def random_values(cell_type):
    if cell_type == "LFP":
        voltage = round(random.uniform(3.0, 3.4), 2)
    else:
        voltage = round(random.uniform(3.4, 3.8), 2)
    current = round(random.uniform(0.0, 2.0), 2)
    temp = round(random.uniform(25, 40), 1)
    capacity = round(voltage * abs(current), 2)
    return voltage, current, temp, capacity

# Input for each cell type
for i in range(1, num_cells + 1):
    cell_types[i] = st.sidebar.selectbox(f"Cell {i} Type", ["LFP", "NMC"], key=f"type_{i}")

# Randomize button
if st.sidebar.button("🎲 Randomize All Initial Values"):
    for i in range(1, num_cells + 1):
        v, c, t, cap = random_values(cell_types[i])
        cell_data[i] = {"Voltage": v, "Current": c, "Temp": t, "Capacity": cap}

# Manual Override
st.sidebar.subheader("Manual Override")
for i in range(1, num_cells + 1):
    if i not in cell_data:
        v, c, t, cap = random_values(cell_types[i])
    else:
        v, c, t, cap = cell_data[i].values()
    
    with st.sidebar.expander(f"Cell {i} ({cell_types[i]}) Settings"):
        v = st.number_input(f"Voltage (Cell {i})", value=v, key=f"volt_{i}")
        c = st.number_input(f"Current (Cell {i})", value=c, key=f"curr_{i}")
        t = st.number_input(f"Temperature (Cell {i})", value=t, key=f"temp_{i}")
        cap = st.number_input(f"Capacity (Cell {i})", value=cap, key=f"cap_{i}")
    
    cell_data[i] = {"Voltage": v, "Current": c, "Temp": t, "Capacity": cap}

# Task configuration
tasks = {}
for i in range(1, num_cells + 1):
    with st.sidebar.expander(f"Tasks for Cell {i} ({cell_types[i]})"):
        num_tasks = st.number_input(f"Number of tasks for Cell {i}", min_value=1, value=2, step=1, key=f"tasks_num_{i}")
        task_list = []
        for t_index in range(1, num_tasks + 1):
            task_type = st.selectbox(f"Task {t_index} Type", ["CC_CV", "IDLE", "CC_CD"], key=f"task_type_{i}_{t_index}")
            duration = st.number_input(f"Task {t_index} Duration (sec)", min_value=1, value=5, step=1, key=f"task_dur_{i}_{t_index}")
            task_list.append({"task_type": task_type, "duration": duration})
        tasks[i] = task_list

# --------------------------
# SIMULATION FUNCTION
# --------------------------
def simulate_task(cell_type, task_type):
    if cell_type == "LFP":
        if task_type == "CC_CV":
            voltage = random.uniform(3.2, 3.6)
            current = random.uniform(1.0, 2.0)
        elif task_type == "CC_CD":
            voltage = random.uniform(2.8, 3.2)
            current = -random.uniform(0.5, 1.5)
        else:
            voltage = random.uniform(3.0, 3.4)
            current = 0
    else:
        if task_type == "CC_CV":
            voltage = random.uniform(3.6, 4.2)
            current = random.uniform(1.0, 2.0)
        elif task_type == "CC_CD":
            voltage = random.uniform(3.0, 3.6)
            current = -random.uniform(0.5, 1.5)
        else:
            voltage = random.uniform(3.4, 3.8)
            current = 0
    temp = random.uniform(25, 40)
    capacity = round(voltage * abs(current), 2)
    return voltage, current, temp, capacity

# --------------------------
# SIMULATION
# --------------------------
start_button = st.sidebar.button("▶ Start Simulation")

if start_button:
    st.subheader("📊 Real-Time Cell Data")
    chart_voltage = st.empty()
    chart_current = st.empty()
    chart_capacity = st.empty()
    status_placeholder = st.empty()

    log_data = []
    total_time = max([sum(task['duration'] for task in tasks[i]) for i in tasks])

    for second in range(total_time):
        for cell_id in range(1, num_cells + 1):
            elapsed = 0
            current_task = None
            for task in tasks[cell_id]:
                elapsed += task['duration']
                if second < elapsed:
                    current_task = task['task_type']
                    break
            if current_task:
                v, c, t, cap = simulate_task(cell_types[cell_id], current_task)
                log_data.append([second, cell_id, cell_types[cell_id], v, c, t, cap, current_task])

        df_live = pd.DataFrame(log_data, columns=["Time", "Cell", "Type", "Voltage", "Current", "Temp", "Capacity", "Task"])
        
        fig_v = px.line(df_live, x="Time", y="Voltage", color="Cell", title="Voltage vs Time")
        chart_voltage.plotly_chart(fig_v, use_container_width=True)

        fig_c = px.line(df_live, x="Time", y="Current", color="Cell", title="Current vs Time")
        chart_current.plotly_chart(fig_c, use_container_width=True)

        fig_cap = px.line(df_live, x="Time", y="Capacity", color="Cell", title="Capacity vs Time")
        chart_capacity.plotly_chart(fig_cap, use_container_width=True)

        status_placeholder.dataframe(df_live.tail(num_cells))
        time.sleep(1)

    # --------------------------
    # PER CELL ANALYSIS
    # --------------------------
    st.subheader("📈 Detailed Cell Analysis")
    df_final = pd.DataFrame(log_data, columns=["Time", "Cell", "Type", "Voltage", "Current", "Temp", "Capacity", "Task"])

    for cell_id in range(1, num_cells + 1):
        st.markdown(f"### 🔍 Analysis for Cell {cell_id} ({cell_types[cell_id]})")
        df_cell = df_final[df_final["Cell"] == cell_id]
        st.write(df_cell.describe()[["Voltage", "Current", "Temp", "Capacity"]])
        
        fig_cell = px.line(df_cell, x="Time", y="Voltage", title=f"Cell {cell_id} Voltage Trend")
        st.plotly_chart(fig_cell, use_container_width=True)

    # --------------------------
    # CSV EXPORT
    # --------------------------
    csv = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(label="📥 Download CSV", data=csv, file_name=f"cell_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
