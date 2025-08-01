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

# Custom Dark Theme CSS
st.markdown("""
    <style>
        .stApp {background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI', sans-serif;}
        h1, h2, h3, h4 {color: #ffffff;}
        .css-1d391kg {background-color: #1E1E1E;}
        .stButton>button {background-color: #FF5722; color: white; border-radius: 8px; padding: 6px 12px;}
        .stButton>button:hover {background-color: #E64A19;}
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --------------------------
# SIDEBAR: CONFIGURATION
# --------------------------
st.sidebar.header("⚙️ Configuration")

# Number of cells
num_cells = st.sidebar.number_input("Number of Cells", min_value=1, value=3, step=1)

# Cell type selection
cell_types = {}
for i in range(1, num_cells + 1):
    cell_types[i] = st.sidebar.selectbox(f"Cell {i} Type", ["LFP", "NMC"], key=f"type_{i}")

# Task configuration dictionary
tasks = {}
for i in range(1, num_cells + 1):
    with st.sidebar.expander(f"Tasks for Cell {i} ({cell_types[i]})"):
        num_tasks = st.number_input(f"Number of tasks for Cell {i}", min_value=1, value=2, step=1, key=f"tasks_num_{i}")
        task_list = []
        for t in range(1, num_tasks + 1):
            task_type = st.selectbox(f"Task {t} Type", ["CC_CV", "IDLE", "CC_CD"], key=f"task_type_{i}_{t}")
            duration = st.number_input(f"Task {t} Duration (sec)", min_value=1, value=5, step=1, key=f"task_dur_{i}_{t}")
            task_list.append({"task_type": task_type, "duration": duration})
        tasks[i] = task_list

# --------------------------
# DATA STORAGE
# --------------------------
data = pd.DataFrame(columns=["Time", "Cell", "Type", "Voltage", "Current", "Temp", "Capacity", "Task"])

# --------------------------
# SIMULATION FUNCTION
# --------------------------
def simulate_task(cell_id, cell_type, task_type):
    """Generate random readings based on task & cell type."""
    if cell_type == "LFP":
        if task_type == "CC_CV":
            voltage = random.uniform(3.2, 3.6)
            current = random.uniform(1.0, 2.0)
        elif task_type == "CC_CD":
            voltage = random.uniform(2.8, 3.2)
            current = -random.uniform(0.5, 1.5)
        else:  # IDLE
            voltage = random.uniform(3.0, 3.4)
            current = 0
    else:  # NMC
        if task_type == "CC_CV":
            voltage = random.uniform(3.6, 4.2)
            current = random.uniform(1.0, 2.0)
        elif task_type == "CC_CD":
            voltage = random.uniform(3.0, 3.6)
            current = -random.uniform(0.5, 1.5)
        else:  # IDLE
            voltage = random.uniform(3.4, 3.8)
            current = 0

    temp = random.uniform(25, 40)
    capacity = round(voltage * abs(current), 2)
    return voltage, current, temp, capacity

# --------------------------
# START SIMULATION
# --------------------------
start_button = st.sidebar.button("▶ Start Simulation")

if start_button:
    st.subheader("📊 Real-Time Cell Data")
    chart_voltage = st.empty()
    chart_current = st.empty()
    chart_capacity = st.empty()

    status_placeholder = st.empty()

    log_data = []

    start_time = time.time()

    for second in range(max([sum(task['duration'] for task in tasks[i]) for i in tasks])):
        for cell_id in range(1, num_cells + 1):
            elapsed_tasks = 0
            current_task = None
            for task in tasks[cell_id]:
                elapsed_tasks += task['duration']
                if second < elapsed_tasks:
                    current_task = task['task_type']
                    break
            if not current_task:
                continue

            v, c, t, cap = simulate_task(cell_id, cell_types[cell_id], current_task)
            log_data.append([second, cell_id, cell_types[cell_id], v, c, t, cap, current_task])

        df_live = pd.DataFrame(log_data, columns=["Time", "Cell", "Type", "Voltage", "Current", "Temp", "Capacity", "Task"])

        # Voltage Graph
        fig_v = px.line(df_live, x="Time", y="Voltage", color="Cell", title="Voltage vs Time")
        chart_voltage.plotly_chart(fig_v, use_container_width=True)

        # Current Graph
        fig_c = px.line(df_live, x="Time", y="Current", color="Cell", title="Current vs Time")
        chart_current.plotly_chart(fig_c, use_container_width=True)

        # Capacity Graph
        fig_cap = px.line(df_live, x="Time", y="Capacity", color="Cell", title="Capacity vs Time")
        chart_capacity.plotly_chart(fig_cap, use_container_width=True)

        status_placeholder.dataframe(df_live.tail(num_cells))

        time.sleep(1)

    # --------------------------
    # POST TEST ANALYSIS
    # --------------------------
    st.subheader("📈 Post-Test Analysis")
    df_final = pd.DataFrame(log_data, columns=["Time", "Cell", "Type", "Voltage", "Current", "Temp", "Capacity", "Task"])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Max Voltage", f"{df_final['Voltage'].max():.2f} V")
        st.metric("Min Voltage", f"{df_final['Voltage'].min():.2f} V")
    with col2:
        st.metric("Max Temp", f"{df_final['Temp'].max():.1f} °C")
        st.metric("Average Current", f"{df_final['Current'].mean():.2f} A")

    st.dataframe(df_final.groupby("Cell").agg({"Voltage": ["min", "max"], "Current": "mean", "Capacity": "max"}))

    # --------------------------
    # CSV EXPORT
    # --------------------------
    csv = df_final.to_csv(index=False).encode("utf-8")
    st.download_button(label="📥 Download CSV", data=csv, file_name=f"cell_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
