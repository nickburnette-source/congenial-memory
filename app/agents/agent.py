import ollama
import queue
import threading

class WorkerAgent:
    def __init__(self, agent_id: int, role: str, task_queue: queue.Queue, report_queue: queue.Queue):
        self.agent_id = agent_id
        self.role = role
        self.task_queue = task_queue
        self.report_queue = report_queue
        self.running = True
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)

    def _run_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                # Specialized LLM call with role
                response = ollama.chat(
                    model=st.session_state.get("MODEL_NAME", "llama3.2"),  # from env
                    messages=[
                        {"role": "system", "content": f"You are an expert {self.role}. Be concise, accurate, and actionable."},
                        {"role": "user", "content": task}
                    ]
                )
                result = response["message"]["content"]
                self.report_queue.put({
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "result": result,
                    "status": "done"
                })
            except queue.Empty:
                continue
            except Exception as e:
                self.report_queue.put({"agent_id": self.agent_id, "result": f"Error: {e}", "status": "error"})