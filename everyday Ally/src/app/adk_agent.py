# src/app/adk_agent.py
"""
Minimal ADK skeleton.

This file demonstrates the pattern:
- Define tool functions (pure Python)
- Register as ADK Tools
- Create an ADK Agent that can call these tools

WARNING: ADK API names may change. This file attempts to import common ADK entrypoints
and shows one way to wire tools to an agent. If your ADK version uses different names,
adjust accordingly using the ADK quickstart docs.

Usage:
    python -m src.app.adk_agent
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    # example ADK import patterns (may differ in your installed version)
    from src.adk import Agent, Tool, ModelSpec, AgentRunner  # hypothetical
    ADK_AVAILABLE = True
except Exception:
    # ADK not installed or different import name
    ADK_AVAILABLE = False

# Tools: simple wrappers around our CalendarTool (from src/app/tools/calendar_tool.py)
from src.app.tools.calendar_tool import Cal

calendar_tool_impl = CalendarTool()

def tool_list_events(user_id: str):
    """ADK Tool wrapper to list events for a user."""
    return calendar_tool_impl.list_events(user_id)

def tool_create_event(user_id: str, event: dict):
    return calendar_tool_impl.create_event(user_id, event)

def start_local_adk_agent():
    if not ADK_AVAILABLE:
        logger.warning("ADK package not available in this environment. Install adk-python to use ADK features.")
        return None

    # The ADK API below is conceptual. See your ADK version's quickstart for exact usage.
    try:
        model_spec = ModelSpec(model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
        tools = [
            Tool(name="list_events", fn=tool_list_events, description="List calendar events for a user"),
            Tool(name="create_event", fn=tool_create_event, description="Create a calendar event for a user"),
        ]
        agent = Agent(name="everyday_planner", model_spec=model_spec, tools=tools)
        runner = AgentRunner(agent)
        runner.start()
        return runner
    except Exception as e:
        logger.exception("Failed to start ADK agent: %s", e)
        raise

if __name__ == "__main__":
    start_local_adk_agent()
