# src/app/agents/fitness_agent.py
import json
from typing import Dict, Any
from src.app.llm.llm_client import generate_text
from src.app.llm.prompts import FITNESS_PROMPT

class FitnessAgent:
    async def generate_fitness_plan(self, availability: Dict[str, Any]) -> Dict[str, Any]:
        # The FITNESS_PROMPT constant is a ready-to-use string in prompts.py
        prompt = FITNESS_PROMPT

        resp = await generate_text(prompt)
        if isinstance(resp, dict) and "json" in resp:
            parsed = resp["json"]
            if isinstance(parsed, dict) and "workout" in parsed:
                return parsed["workout"]
        text = resp.get("text") if isinstance(resp, dict) else None
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "workout" in parsed:
                    return parsed["workout"]
            except Exception:
                pass

        # fallback
        return {"workout": "30 min walk + 10 min stretching"}
