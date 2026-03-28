import streamlit as st
import time
import queue
import threading
from agents.supervisor import Supervisor

st.set_page_config(page_title="DGX Spark Multi-Agent Supervisor", layout="wide")
st.title("🧠 DGX Spark Multi-Agent System")
st.caption("Supervisor controls dynamic agent fleet • Ollama on host • SQLite persistence")

# Session state
if "supervisor" not in st.session_state:
    report_queue = queue.Queue()
    st.session_state.supervisor = Supervisor(report_queue)
    st.session_state.progress = []
    st.session_state.active_task = None
    st.session_state.running_thread = None

sup = st.session_state.supervisor
model_name = st.session_state.get("MODEL_NAME", "llama3.2")  # fallback

# Sidebar fleet status
st.sidebar.header("Fleet Status")
if sup.agents:
    for aid, agent in sup.agents.items():
        status = "🟢 working" if agent["status"] == "working" else "⚪ idle"
        st.sidebar.write(f"Agent {aid} ({agent['role']}) → {status}")
else:
    st.sidebar.info("No agents active yet — supervisor creates them on demand")

# Main task input
task = st.text_area("Enter task for the Supervisor:", 
                    placeholder="Example: Research the best way to fine-tune a small LLM on DGX Spark and write a simple training script.",
                    height=120)

if st.button("🚀 Start Supervisor Task", type="primary", use_container_width=True):
    if task.strip():
        st.session_state.active_task = task
        st.session_state.progress = []
        
        def run_supervisor():
            try:
                sup.run_task(task, model_name=model_name)   # pass model safely
            except Exception as e:
                sup.progress.append({"message": f"💥 Supervisor crashed: {e}"})
        
        st.session_state.running_thread = threading.Thread(target=run_supervisor, daemon=True)
        st.session_state.running_thread.start()
        st.success("Task submitted to Supervisor. Live updates below...")

# Live progress area
if st.session_state.active_task:
    st.subheader("📋 Live Progress & Agent Reports")
    progress_container = st.container()
    
    # Poll while thread is alive
    while (st.session_state.running_thread and 
           st.session_state.running_thread.is_alive()):
        with progress_container:
            for msg in st.session_state.progress[-15:]:
                if isinstance(msg, dict):
                    if "agent_id" in msg:
                        st.write(f"**Agent {msg['agent_id']}** ({msg.get('role','')}) → {msg.get('result','')[:400]}...")
                    else:
                        st.info(msg.get("message", str(msg)))
        time.sleep(1.5)
        st.rerun()

    # Show final results when done
    if not (st.session_state.running_thread and st.session_state.running_thread.is_alive()):
        st.success("✅ Supervisor task finished!")
        for msg in st.session_state.progress:
            if isinstance(msg, dict) and "result" in msg and "agent_id" not in msg:
                st.markdown("### Final Answer")
                st.write(msg["result"])
        st.session_state.active_task = None

st.divider()
st.caption("Architecture: Supervisor → decomposes task → creates/destroys agents dynamically → agents report via queue → SQLite logging. All on single DGX Spark.")