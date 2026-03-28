import ollama
import json
import queue
import time
from .agent import WorkerAgent
import streamlit as st  # only for model name fallback

class Supervisor:
    def __init__(self, report_queue: queue.Queue):
        self.report_queue = report_queue
        self.agents: dict = {}  # agent_id -> {"agent": WorkerAgent, "thread": Thread, "role": str, "status": str}
        self.next_agent_id = 0
        self.progress = []  # shared with UI via session_state

    def create_agent(self, role: str) -> int:
        """Dynamically create a new worker agent"""
        agent_id = self.next_agent_id
        self.next_agent_id += 1
        
        task_queue = queue.Queue()
        agent = WorkerAgent(agent_id, role, task_queue, self.report_queue)
        agent.start()
        
        self.agents[agent_id] = {
            "agent": agent,
            "role": role,
            "status": "idle",
            "task_queue": task_queue
        }
        self.progress.append({"message": f"✅ Created Agent {agent_id} as {role}"})
        return agent_id

    def destroy_agent(self, agent_id: int):
        """Dynamically destroy an agent"""
        if agent_id in self.agents:
            self.agents[agent_id]["agent"].stop()
            del self.agents[agent_id]
            self.progress.append({"message": f"🗑️ Destroyed Agent {agent_id}"})

    def run_task(self, user_task: str):
        """Main supervisor loop: decompose → assign → collect → decide if complete"""
        self.progress.append({"message": f"📥 Received task: {user_task[:100]}..."})
        
        # Step 1: Supervisor uses Ollama to break down task into subtasks + roles
        plan_prompt = f"""
        You are the Supervisor. Break this user task into 2-5 parallel subtasks.
        For each subtask, assign a clear specialized ROLE (e.g., researcher, coder, analyst, writer).
        Return ONLY valid JSON array like: [{"role": "researcher", "subtask": "..."}, ...]
        Task: {user_task}
        """
        try:
            resp = ollama.chat(
                model=st.session_state.get("MODEL_NAME", "llama3.2"),
                messages=[{"role": "user", "content": plan_prompt}]
            )
            plan_text = resp["message"]["content"]
            subtasks = json.loads(plan_text)
        except Exception:
            # Fallback
            subtasks = [{"role": "general-agent", "subtask": user_task}]

        self.progress.append({"message": f"📋 Decomposed into {len(subtasks)} subtasks"})

        # Step 2: Create/destroy agents dynamically & assign work
        assigned = {}
        for sub in subtasks:
            role = sub["role"]
            # Reuse existing agent with same role if possible, else create
            existing_id = next((aid for aid, a in self.agents.items() if a["role"] == role), None)
            agent_id = existing_id if existing_id is not None else self.create_agent(role)
            
            self.agents[agent_id]["status"] = "working"
            self.agents[agent_id]["task_queue"].put(sub["subtask"])
            assigned[agent_id] = sub["subtask"]

        # Step 3: Collect reports until all agents done (simple loop)
        done_count = 0
        while done_count < len(assigned):
            try:
                report = self.report_queue.get(timeout=5)
                self.progress.append(report)
                if report.get("status") == "done":
                    done_count += 1
                    # Mark agent idle again
                    aid = report["agent_id"]
                    if aid in self.agents:
                        self.agents[aid]["status"] = "idle"
            except queue.Empty:
                continue

        # Step 4: Final supervisor synthesis (optional final LLM call)
        self.progress.append({"message": "🔄 Supervisor synthesizing final answer..."})
        final_prompt = f"Summarize all agent reports into a single coherent final answer for the user:\n{user_task}\nReports: {str(self.progress[-10:])}"
        final_resp = ollama.chat(
            model=st.session_state.get("MODEL_NAME", "llama3.2"),
            messages=[{"role": "user", "content": final_prompt}]
        )
        self.progress.append({"message": "✅ Final answer ready", "result": final_resp["message"]["content"]})

        # Optional cleanup of idle agents (demo of destroy)
        if len(self.agents) > 3:  # keep fleet small
            for aid in list(self.agents.keys())[:2]:
                self.destroy_agent(aid)