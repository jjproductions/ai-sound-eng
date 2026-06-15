import json
import urllib.request
from .prompts import HERMES_SYSTEM_PROMPT

class HermesAgent:
    """
    Interfaces with a local Ollama instance running the Hermes cognitive layer.
    """
    def __init__(self, model_name="llama3"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def evaluate_features(self, features_json: str, track_name: str) -> dict:
        """
        Sends the analyzed features to Ollama and returns the recommended mixing action.
        """
        prompt = f"Target Track: {track_name}\nAnalyzed Acoustic Features:\n{features_json}\nWhat mix action do you recommend?"
        
        payload = {
            "model": self.model_name,
            "system": HERMES_SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            req = urllib.request.Request(
                self.api_url, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            response_text = result.get("response", "{}")
            
            # Basic validation
            decision = json.loads(response_text)
            if "action" not in decision:
                raise ValueError("LLM response missing 'action' field.")
                
            return decision
            
        except Exception as e:
            print(f"Hermes Agent Error: {e}")
            return {
                "reasoning": f"Failed to connect to Ollama or parse response: {str(e)}",
                "action": None
            }
