import requests
import json
import time

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://ollama:11434"
        self.timeout = 120  # seconds - generous for DGX Spark

    def chat(self, model: str, messages: list, options: dict = None):
        """Direct /api/chat call with timeout and heartbeat-ready response."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options or {"temperature": 0.7, "num_predict": 1024}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API error: {e} (status {getattr(e.response, 'status_code', 'unknown')})")