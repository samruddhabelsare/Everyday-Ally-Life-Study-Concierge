# src/app/agents/planner_agent.py

import asyncio
from typing import Dict, Any

from src.app.agents.study_agent import StudyAgent
from src.app.agents.nutrition_agent import NutritionAgent
from src.app.agents.fitness_agent import FitnessAgent
from src.app.memory.memory_bank import MemoryBank


class PlannerAgent:
    """Orchestrates multiple agents to generate one daily plan."""

    def __init__(self, memory: MemoryBank):
        self.memory = memory
        self.study_agent = StudyAgent()
        self.nutrition_agent = NutritionAgent()
        self.fitness_agent = FitnessAgent()

    async def plan_day(self, user_id: str, availability: Dict[str, Any]) -> Dict[str, Any]:
        tasks = [
            self.study_agent.generate_study_blocks(availability),
            self.nutrition_agent.generate_meals(availability),
            self.fitness_agent.generate_fitness_plan(availability),
        ]

        study_blocks, meals, workout = await asyncio.gather(*tasks)

        plan = {
            "user_id": user_id,
            "study_blocks": study_blocks,
            "meals": meals,
            "workout": workout,
        }

        self.memory.save_plan(user_id, plan)
        return plan
