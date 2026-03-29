import json
import queue
import time
from .agent import WorkerAgent
from .db import log_task, log_agent_report
from .ollama_client import OllamaClient

class Supervisor:
    def __init__(self, report_queue: queue.Queue):
        self.report_queue = report_queue
        self.agents: dict = {}
        self.next_agent_id = 0
        self.progress = []
        self.task_id = None
        self.client = OllamaClient()
        self.shared_context = {}  # Supervisor-controlled context for all agents

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
        self.shared_context = {"original_task": user_task, "agent_reports": []}  # Supervisor starts controlling context

        # Planning step
        plan_prompt = f"""
You are the Supervisor on DGX Spark. Break this task into 2-5 parallel subtasks.
Return ONLY valid JSON array: [{"role": "role_name", "subtask": "description"}]
Task: {user_task}
"""
        try:
            resp = self.client.chat(messages=[{"role": "user", "content": plan_prompt}])
            plan_text = resp["message"]["content"].strip()
            if "```" in plan_text:
                plan_text = plan_text.split("```")[1].strip()
            subtasks = json.loads(plan_text)
        except Exception:
            subtasks = [{"role": "general-agent", "subtask": user_task}]

        self.progress.append({"message": f"📋 Decomposed into {len(subtasks)} subtasks"})

        # Assign work with shared context injected
        assigned = {}
        for sub in subtasks:
            role = sub.get("role", "general-agent")
            subtask = sub.get("subtask", sub.get("description", ""))
            # Supervisor injects full context into every agent
            full_subtask = f"Context: {self.shared_context['original_task']}\n\nSubtask: {subtask}"
            
            existing_id = next((aid for aid, a in self.agents.items() if a["role"] == role), None)
            agent_id = existing_id if existing_id is not None else self.create_agent(role)
            self.agents[agent_id]["status"] = "working"
            self.agents[agent_id]["task_queue"].put(full_subtask)
            assigned[agent_id] = subtask

        # Collect reports and update shared context
        done_count = 0
        while done_count < len(assigned):
            try:
                report = self.report_queue.get(timeout=15)
                self.progress.append(report)
                if report.get("status") == "done":
                    done_count += 1
                    aid = report["agent_id"]
                    if aid in self.agents:
                        self.agents[aid]["status"] = "idle"
                    log_agent_report(self.task_id, aid, report.get("role", ""), report.get("result", ""))
                    # Supervisor updates shared context automatically
                    self.shared_context["agent_reports"].append(report)
            except queue.Empty:
                continue

        # Final synthesis (simple & reliable - no more 404)
        self.progress.append({"message": "🔄 Supervisor synthesizing final answer..."})
        agent_summaries = "\n".join(
            f"Agent {p.get('agent_id')} ({p.get('role')}): {p.get('result', '')[:800]}"
            for p in self.progress if isinstance(p, dict) and p.get("status") == "done"
        )
        final_result = f"""
Final Answer (supervisor-controlled synthesis):

{agent_summaries}

(Supervisor has full context and can reuse agents for follow-up tasks.)
"""
        self.progress.append({"message": "✅ Task complete", "result": final_result})

        # Light cleanup (supervisor decides when to destroy agents)
        if len(self.agents) > 5:
            for aid in list(self.agents.keys())[:2]:
                if self.agents[aid]["status"] == "idle":
                    self.destroy_agent(aid)