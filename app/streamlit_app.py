import streamlit as st
import time
import queue
import threading
from agents.supervisor import Supervisor

st.set_page_config(page_title="DGX Spark Multi-Agent Supervisor", layout="wide")
st.title("🧠 DGX Spark Multi-Agent System")
st.caption("Supervisor + dynamic agent fleet • Powered by Ollama on host • MSSQL ready")

# Session state for supervisor and progress
if "supervisor" not in st.session_state:
    report_queue = queue.Queue()
    st.session_state.supervisor = Supervisor(report_queue)
    st.session_state.progress = []
    st.session_state.active_task = None
    st.session_state.running_thread = None

sup = st.session_state.supervisor

# Sidebar: Live fleet status
st.sidebar.header("Fleet Status")
if st.session_state.supervisor.agents:
    for aid, agent in st.session_state.supervisor.agents.items():
        status = "🟢 working" if agent["status"] == "working" else "⚪ idle"
        st.sidebar.write(f"Agent {aid} ({agent['role']}) → {status}")
else:
    st.sidebar.info("No agents yet — supervisor will create them automatically")

# Main UI
task = st.text_area("Enter task for the Supervisor to break down and execute:", 
                    placeholder="Example: Analyze the latest sales data and generate a Python script to visualize trends.",
                    height=100)

col1, col2 = st.columns([1, 3])
if col1.button("🚀 Start Supervisor Task", type="primary", use_container_width=True):
    if task.strip():
        st.session_state.active_task = task
        st.session_state.progress = []
        
        # Run supervisor in background thread so UI stays responsive
        def run_supervisor():
            sup.run_task(task)
        
        st.session_state.running_thread = threading.Thread(target=run_supervisor, daemon=True)
        st.session_state.running_thread.start()
        
        st.success("Task submitted! Watch the live progress below.")

if st.session_state.active_task:
    st.subheader("📋 Live Progress & Agent Reports")
    progress_container = st.container()
    
    # Live update loop (rerun every 2s while running)
    while st.session_state.running_thread and st.session_state.running_thread.is_alive():
        with progress_container:
            for msg in st.session_state.progress[-10:]:  # last 10 messages
                if msg.get("agent_id") is not None:
                    st.write(f"**Agent {msg['agent_id']}** ({msg.get('role', 'unknown')}): {msg['result'][:300]}...")
                else:
                    st.info(msg["message"])
        time.sleep(2)
        st.rerun()

    # Final results
    if not st.session_state.running_thread or not st.session_state.running_thread.is_alive():
        st.success("✅ Task complete! Supervisor loop finished.")
        for msg in st.session_state.progress:
            if msg.get("agent_id"):
                st.write(f"**Agent {msg['agent_id']}** final result: {msg['result']}")
        st.session_state.active_task = None

# Footer info
st.divider()
st.caption("🛠️ Architecture: Supervisor decomposes → creates/destroys agents → agents report via queue → UI polls live.")