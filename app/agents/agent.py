import queue
import time
import threading
from .ollama_client import OllamaClient

class WorkerAgent:
    def __init__(self, agent_id: int, role: str, task_queue: queue.Queue, report_queue: queue.Queue):
        self.agent_id = agent_id
        self.role = role
        self.task_queue = task_queue
        self.report_queue = report_queue
        self.running = True
        self.thread = None
        self.client = OllamaClient()  # points to ollama service

    def start(self):
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _run_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)

                # Immediate status so UI shows activity
                self.report_queue.put({
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "result": "Starting inference on Ollama (DGX Spark)...",
                    "status": "working"
                })

                start_time = time.time()
                heartbeat_thread = None

                def send_heartbeat():
                    while time.time() - start_time < 120 and self.running:
                        elapsed = int(time.time() - start_time)
                        self.report_queue.put({
                            "agent_id": self.agent_id,
                            "role": self.role,
                            "result": f"Still thinking... ({elapsed}s elapsed on DGX Spark)",
                            "status": "working"
                        })
                        time.sleep(8)

                heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
                heartbeat_thread.start()

                # System prompt + user task
                messages = [
                    {"role": "system", "content": f"You are an expert {self.role}. Be concise, accurate, and actionable."},
                    {"role": "user", "content": task}
                ]

                response = self.client.chat(
                    model="llama3.2:1b",  # matches your env
                    messages=messages
                )
                result = response["message"]["content"]
                elapsed = time.time() - start_time

                self.report_queue.put({
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "result": f"{result}\n\n(Completed in {elapsed:.1f}s)",
                    "status": "done"
                })

            except queue.Empty:
                continue
            except Exception as e:
                elapsed = int(time.time() - start_time) if 'start_time' in locals() else 0
                self.report_queue.put({
                    "agent_id": self.agent_id,
                    "role": self.role,
                    "result": f"Error after {elapsed}s: {str(e)[:400]}",
                    "status": "error"
                })
            finally:
                if heartbeat_thread and heartbeat_thread.is_alive():
                    heartbeat_thread.join(timeout=1)