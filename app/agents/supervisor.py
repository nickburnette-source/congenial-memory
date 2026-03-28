import ollama
import json
import queue
import time
from .agent import WorkerAgent
from .db import log_task, log_agent_report
import streamlit as st

class Supervisor:
    def __init__(self, report_queue: queue.Queue):
        self.report_queue = report_queue
        self.agents: dict = {}
        self.next_agent_id = 0
        self.progress = []
        self.task_id = None  # for DB logging

    def create_agent(self, role: str) -> int:
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
        if agent_id in self.agents:
            self.agents[agent_id]["agent"].stop()
            del self.agents[agent_id]
            self.progress.append({"message": f"🗑️ Destroyed Agent {agent_id}"})

    def run_task(self, user_task: str):
        self.progress.append({"message": f"📥 Received task: {user_task[:100]}..."})
        self.task_id = log_task(user_task)

        # Supervisor decomposition (same as before)
        plan_prompt = f"""
        You are the Supervisor. Break this user task into 2-5 parallel subtasks.
        For each subtask, assign a clear specialized ROLE.
        Return ONLY valid JSON array: [{"role": "...", "subtask": "..."}, ...]
        Task: {user_task}
        """
        try:
            resp = ollama.chat(model=st.session_state.get("MODEL_NAME", "llama3.2"),
                               messages=[{"role": "user", "content": plan_prompt}])
            subtasks = json.loads(resp["message"]["content"])
        except Exception:
            subtasks = [{"role": "general-agent", "subtask": user_task}]

        self.progress.append({"message": f"📋 Decomposed into {len(subtasks)} subtasks"})

        assigned = {}
        for sub in subtasks:
            role = sub["role"]
            existing_id = next((aid for aid, a in self.agents.items() if a["role"] == role), None)
            agent_id = existing_id if existing_id is not None else self.create_agent(role)
            self.agents[agent_id]["status"] = "working"
            self.agents[agent_id]["task_queue"].put(sub["subtask"])
            assigned[agent_id] = sub["subtask"]

        # Collect reports
        done_count = 0
        while done_count < len(assigned):
            try:
                report = self.report_queue.get(timeout=5)
                self.progress.append(report)
                if report.get("status") == "done":
                    done_count += 1
                    aid = report["agent_id"]
                    if aid in self.agents:
                        self.agents[aid]["status"] = "idle"
                    log_agent_report(self.task_id, aid, report.get("role", ""), report["result"])
            except queue.Empty:
                continue

        # Final synthesis
        self.progress.append({"message": "🔄 Supervisor synthesizing final answer..."})
        final_prompt = f"Summarize all agent reports into one coherent final answer:\nTask: {user_task}\nReports: {str([p for p in self.progress if 'result' in p][-10:])}"
        final_resp = ollama.chat(model=st.session_state.get("MODEL_NAME", "llama3.2"),
                                 messages=[{"role": "user", "content": final_prompt}])
        final_result = final_resp["message"]["content"]
        self.progress.append({"message": "✅ Task complete", "result": final_result})

        # Optional cleanup
        if len(self.agents) > 4:
            for aid in list(self.agents.keys())[:2]:
                self.destroy_agent(aid)