# src/app/agents/study_agent.py
import asyncio
import json
from typing import Dict, List, Any
from src.app.llm.llm_client import generate_text
from src.app.llm.prompts import study_prompt

class StudyAgent:
    async def generate_study_blocks(self, availability: Dict[str, Any]) -> List[Dict]:
        topics = availability.get("topics", [])
        hours = availability.get("hours", 3)
        blocks = availability.get("blocks", 2)

        prompt = study_prompt(hours=hours, topics=topics, blocks=blocks)

        # call the LLM via the async helper
        resp = await generate_text(prompt)
        # try to return structured JSON if present
        if isinstance(resp, dict) and "json" in resp:
            parsed = resp["json"]
            if isinstance(parsed, dict) and "study_blocks" in parsed:
                return parsed["study_blocks"]
        # fallback: try parsing text
        text = resp.get("text") if isinstance(resp, dict) else None
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "study_blocks" in parsed:
                    return parsed["study_blocks"]
            except Exception:
                pass

        # deterministic fallback
        block_len = max(25, int((hours * 60) / max(1, blocks)))
        return [{"title": f"Study Block {i+1}", "duration_min": block_len, "goal": "Study focus"} for i in range(blocks)]
