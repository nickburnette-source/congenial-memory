import requests
import json
import time
import os

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://ollama:11434"
        self.timeout = 120
        self.model = os.getenv("MODEL_NAME", "llama3.2:1b")  # respects your .env/docker env

    def chat(self, messages: list, options: dict = None):
        """Direct /api/chat with timeout, safe context, and debug logging"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options or {"temperature": 0.7, "num_predict": 512, "num_ctx": 8192}  # safe for 1B model
        }
        
        try:
            print(f"[DEBUG] Ollama request to {self.model} | messages: {len(messages)}")  # visible in docker logs
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            status = getattr(e.response, 'status_code', 'unknown')
            print(f"[ERROR] Ollama API failed: {status} - {str(e)[:300]}")  # debug
            raise RuntimeError(f"Ollama API error {status}: {e}")