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

    # create_agent and destroy_agent stay exactly the same as before
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
        self.progress.append({"message": f"📥 Received task: {user_task[:100]}..."})
        self.task_id = log_task(user_task)

        # Supervisor planning step
        plan_prompt = f"""
You are the Supervisor of a multi-agent system on DGX Spark.
Break this user task into 2-5 parallel subtasks.
For each subtask, assign a clear specialized ROLE.
Return ONLY valid JSON array: [{{"role": "role_name", "subtask": "detailed subtask"}}]
Task: {user_task}
"""
        try:
            resp = self.client.chat(
                model=model_name,
                messages=[{"role": "user", "content": plan_prompt}]
            )
            plan_text = resp["message"]["content"].strip()
            # Clean markdown if present
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            subtasks = json.loads(plan_text)
        except Exception as e:
            self.progress.append({"message": f"⚠️ Planning failed ({e}), using fallback"})
            subtasks = [{"role": "general-agent", "subtask": user_task}]

        self.progress.append({"message": f"📋 Decomposed into {len(subtasks)} subtasks"})

        # Assign to agents (reuse same-role agents when possible)
        assigned = {}
        for sub in subtasks:
            role = sub.get("role", "general-agent")
            subtask = sub.get("subtask", sub.get("description", ""))
            existing_id = next((aid for aid, a in self.agents.items() if a["role"] == role), None)
            agent_id = existing_id if existing_id is not None else self.create_agent(role)
            self.agents[agent_id]["status"] = "working"
            self.agents[agent_id]["task_queue"].put(subtask)
            assigned[agent_id] = subtask

        # Collect reports
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
            except queue.Empty:
                continue

        # Final supervisor synthesis
        self.progress.append({"message": "🔄 Supervisor synthesizing final answer..."})
        final_prompt = f"""
Summarize the following agent reports into ONE clear, coherent final answer.
Task: {user_task}

Reports: {str([p for p in self.progress if isinstance(p, dict) and "result" in p][-10:])}
"""
        try:
            final_resp = self.client.chat(model=model_name, messages=[{"role": "user", "content": final_prompt}])
            final_result = final_resp["message"]["content"]
        except Exception as e:
            final_result = f"Synthesis failed: {e}"

        self.progress.append({"message": "✅ Task complete", "result": final_result})

        # Light cleanup
        if len(self.agents) > 5:
            for aid in list(self.agents.keys())[:2]:
                if self.agents[aid]["status"] == "idle":
                    self.destroy_agent(aid)