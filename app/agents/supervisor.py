import ollama
import json
import queue
import time
from .agent import WorkerAgent
from .db import log_task, log_agent_report

class Supervisor:
    def __init__(self, report_queue: queue.Queue):
        self.report_queue = report_queue
        self.agents: dict = {}
        self.next_agent_id = 0
        self.progress = []
        self.task_id = None

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

    def run_task(self, user_task: str, model_name: str = "llama3.2:1b"):
        """Main supervisor loop. model_name is passed from main thread to avoid session_state issues."""
        self.progress.append({"message": f"📥 Received task: {user_task[:100]}..."})
        self.task_id = log_task(user_task)

        # Fixed prompt: double curly braces so f-string doesn't misinterpret JSON
        plan_prompt = f"""
You are the Supervisor of a multi-agent system.
Break this user task into 2-5 parallel subtasks that can run concurrently.
For each subtask, assign a clear specialized ROLE (e.g. researcher, coder, analyst, writer, debugger).

Return ONLY a valid JSON array in this exact format (no extra text, no markdown):
[{{"role": "role_name", "subtask": "detailed subtask description"}}]

User task: {user_task}
"""

        try:
            resp = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": plan_prompt}]
            )
            plan_text = resp["message"]["content"].strip()
            # Clean possible markdown code block
            if plan_text.startswith("```json"):
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif plan_text.startswith("```"):
                plan_text = plan_text.split("```")[1].strip()
            subtasks = json.loads(plan_text)
        except Exception as e:
            self.progress.append({"message": f"⚠️ Planning failed ({e}), using fallback"})
            subtasks = [{"role": "general-agent", "subtask": user_task}]

        self.progress.append({"message": f"📋 Decomposed into {len(subtasks)} subtasks"})

        # Assign work (reuse agents with same role when possible)
        assigned = {}
        for sub in subtasks:
            role = sub.get("role", "general-agent")
            subtask = sub.get("subtask", sub.get("description", ""))

            existing_id = next((aid for aid, a in self.agents.items() if a["role"] == role), None)
            agent_id = existing_id if existing_id is not None else self.create_agent(role)

            self.agents[agent_id]["status"] = "working"
            self.agents[agent_id]["task_queue"].put(subtask)
            assigned[agent_id] = subtask

        # Collect reports from agents
        done_count = 0
        target = len(assigned)
        while done_count < target:
            try:
                report = self.report_queue.get(timeout=8)
                self.progress.append(report)
                if report.get("status") == "done":
                    done_count += 1
                    aid = report["agent_id"]
                    if aid in self.agents:
                        self.agents[aid]["status"] = "idle"
                    log_agent_report(self.task_id, aid, report.get("role", ""), report.get("result", ""))
            except queue.Empty:
                continue

        # Final synthesis by supervisor
        self.progress.append({"message": "🔄 Supervisor synthesizing final answer..."})
        final_prompt = f"""
Summarize the following agent reports into ONE clear, coherent final answer for the user.
Task: {user_task}

Agent reports:
{str([p for p in self.progress if isinstance(p, dict) and "result" in p][-15:])}
"""

        try:
            final_resp = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": final_prompt}]
            )
            final_result = final_resp["message"]["content"]
        except Exception:
            final_result = "Synthesis failed - raw agent outputs attached."

        self.progress.append({"message": "✅ Task complete", "result": final_result})

        # Light cleanup of excess idle agents
        if len(self.agents) > 5:
            for aid in list(self.agents.keys())[:2]:
                if self.agents[aid]["status"] == "idle":
                    self.destroy_agent(aid)