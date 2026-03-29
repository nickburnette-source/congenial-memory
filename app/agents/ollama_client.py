import requests
import time
import os

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://ollama:11434"
        self.timeout = 120
        self.model = os.getenv("MODEL_NAME", "llama3.2:1b")

    def chat(self, messages: list, options: dict = None):
        """Reliable /api/chat with retry on 404/timeout (DGX Spark runner quirk)"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options or {"temperature": 0.7, "num_predict": 512, "num_ctx": 8192}
        }
        
        for attempt in range(3):  # retry up to 3 times
            try:
                response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
                if response.status_code == 404:
                    time.sleep(1)  # brief wait for runner
                    continue
                response.raise_for_status()
                return response.json()
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)
        raise RuntimeError("Ollama /api/chat failed after retries")