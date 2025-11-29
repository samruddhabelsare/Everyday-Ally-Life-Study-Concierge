# src/app/agents/nutrition_agent.py
import asyncio
import json
from typing import Dict, List, Any
from src.app.llm.llm_client import generate_text
from src.app.llm.prompts import nutrition_prompt

class NutritionAgent:
    async def generate_meals(self, availability: Dict[str, Any]) -> List[Dict]:
        diet = availability.get("diet", "omnivore")
        prompt = nutrition_prompt(diet=diet)

        resp = await generate_text(prompt)
        # structured parse if available
        if isinstance(resp, dict) and "json" in resp:
            parsed = resp["json"]
            if isinstance(parsed, dict) and "meals" in parsed:
                return parsed["meals"]
        # try parsing free text
        text = resp.get("text") if isinstance(resp, dict) else None
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "meals" in parsed:
                    return parsed["meals"]
            except Exception:
                pass

        # fallback hardcoded suggestions
        if diet == "vegetarian":
            return [
                {"meal": "Veggie omelette", "desc": "Eggs with vegetables", "cal": 350},
                {"meal": "Quinoa salad", "desc": "Quinoa with mixed veg", "cal": 420},
            ]
        return [
            {"meal": "Grilled chicken & rice", "desc": "Lean protein + rice", "cal": 550},
            {"meal": "Pasta primavera", "desc": "Pasta with vegetables", "cal": 480},
        ]
