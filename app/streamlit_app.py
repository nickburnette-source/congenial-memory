import streamlit as st
import time
import queue
import threading
from agents.supervisor import Supervisor

st.set_page_config(page_title="DGX Spark Multi-Agent Supervisor", layout="wide")
st.title("🧠 DGX Spark Multi-Agent System")
st.caption("Supervisor controls fleet + shared context • GPU Ollama • SQLite persistence")

if "supervisor" not in st.session_state:
    report_queue = queue.Queue()
    st.session_state.supervisor = Supervisor(report_queue)
    st.session_state.progress = []
    st.session_state.active_task = None
    st.session_state.running_thread = None

sup = st.session_state.supervisor

# Sidebar fleet status
st.sidebar.header("Fleet Status")
if sup.agents:
    for aid, agent in sup.agents.items():
        status = "🟢 working" if agent["status"] == "working" else "⚪ idle"
        st.sidebar.write(f"Agent {aid} ({agent['role']}) → {status}")
else:
    st.sidebar.info("Waiting for Supervisor to create agents...")

# Task input
task = st.text_area("Enter task for the Supervisor:", 
                    placeholder="Example: Write a short poem about DGX Spark and blockchain.",
                    height=120)

if st.button("🚀 Start Supervisor Task", type="primary", use_container_width=True):
    if task.strip():
        st.session_state.active_task = task
        st.session_state.progress = []
        
        def run_supervisor():
            try:
                sup.run_task(task)
            except Exception as e:
                sup.progress.append({"message": f"💥 Supervisor error: {e}"})
        
        st.session_state.running_thread = threading.Thread(target=run_supervisor, daemon=True)
        st.session_state.running_thread.start()
        st.success("Task submitted — Supervisor + fleet are now working...")

# Live progress (always visible while task active)
if st.session_state.active_task:
    st.subheader("📋 Live Progress & Agent Reports")
    progress_container = st.container()

    if st.button("🔄 Force Refresh Now", use_container_width=True):
        st.rerun()

    # Poll aggressively while agents are running
    while st.session_state.running_thread and st.session_state.running_thread.is_alive():
        with progress_container:
            # Show any "working" messages prominently
            working_msgs = [msg for msg in st.session_state.progress[-20:] 
                           if isinstance(msg, dict) and msg.get("status") == "working"]
            if working_msgs:
                st.warning("**Agents are actively working on DGX Spark** (inference can take 30-90s each)")
                for msg in working_msgs:
                    st.write(f"**Agent {msg['agent_id']}** ({msg.get('role','')}) → {msg.get('result','')}")
            else:
                for msg in st.session_state.progress[-15:]:
                    if isinstance(msg, dict):
                        if "agent_id" in msg:
                            st.write(f"**Agent {msg['agent_id']}** ({msg.get('role','')}) → {msg.get('result','')[:500]}...")
                        else:
                            st.info(msg.get("message", str(msg)))
        time.sleep(2)   # poll every 2 seconds
        st.rerun()

    # Final results when done
    if not (st.session_state.running_thread and st.session_state.running_thread.is_alive()):
        st.success("✅ Supervisor task finished!")
        final_msg = next((msg for msg in reversed(st.session_state.progress) if isinstance(msg, dict) and "result" in msg), None)
        if final_msg:
            st.markdown("### 🏁 Final Answer")
            st.write(final_msg["result"])
        st.session_state.active_task = None

st.divider()
st.caption("Supervisor → decomposes task → controls shared context → creates/destroys agents at will → agents report via queue")