# src/app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# App agents & memory (use package imports - src must be on PYTHONPATH)
from app.agents.input_agent import InputAgent
from app.agents.planner_agent import PlannerAgent
from app.memory.memory_bank import MemoryBank
from app.agents.reminder_agent import ReminderAgent

# Optional ADK wrappers (we will create this file next)
# It provides adk planner agent wrappers if google ADK is installed.
from app.adk_wrappers import adk_planner, ensure_adk_ready

app = FastAPI(title="Everyday Ally API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons used by API and Streamlit UI
memory = MemoryBank()
input_agent = InputAgent()
# Instantiate your PlannerAgent implementation (keeps original logic)
planner = PlannerAgent(memory=memory)

# If ADK is available we register or expose ADK agent wrappers.
ADK_AVAILABLE = ensure_adk_ready(planner=planner, memory=memory)

# instantiate ReminderAgent singleton (long-running background loop)
reminder_agent = ReminderAgent(memory=memory)

# --- Reminder endpoints ---
@app.post("/reminder/create")
async def create_reminder(payload: dict):
    user_id = payload.get("user_id", "demo_user")
    when_iso = payload.get("when_iso")
    message = payload.get("message", "")
    reminder = reminder_agent.schedule_reminder(user_id=user_id, when_iso=when_iso, message=message)
    return {"status": "ok", "reminder": reminder}

@app.get("/reminder/list/{user_id}")
async def list_reminders(user_id: str):
    items = reminder_agent.list_reminders(user_id)
    return {"status": "ok", "reminders": items}

@app.post("/reminder/cancel")
async def cancel_reminder(payload: dict):
    user_id = payload.get("user_id", "demo_user")
    reminder_id = payload.get("reminder_id")
    ok = reminder_agent.cancel_reminder(user_id, reminder_id)
    return {"status": "ok", "cancelled": ok}

@app.post("/reminder/snooze")
async def snooze_reminder(payload: dict):
    user_id = payload.get("user_id", "demo_user")
    reminder_id = payload.get("reminder_id")
    minutes = int(payload.get("minutes", 10))
    updated = reminder_agent.snooze_reminder(user_id, reminder_id, minutes=minutes)
    return {"status": "ok", "reminder": updated}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/plan/day")
async def plan_day(payload: dict):
    """
    Endpoint to generate a daily plan. This will call the ADK planner agent
    if ADK is available; otherwise it calls the PlannerAgent implementation.
    """
    user_id = payload.get("user_id", "demo_user")
    availability = payload.get("availability", {})

    # If ADK wrapper is available, use it (it may be async)
    if ADK_AVAILABLE and adk_planner is not None:
        # adk_planner is an ADK agent function; it may expect a context object.
        # Our adk wrapper returns a callable that will run and return a plan dict.
        plan = await adk_planner.run(user_id=user_id, availability=availability)  # wrapper provides `.run(...)`
    else:
        # Fallback to existing synchronous/async planner logic
        plan = await planner.plan_day(user_id=user_id, availability=availability)

    return {"status": "ok", "plan": plan}
