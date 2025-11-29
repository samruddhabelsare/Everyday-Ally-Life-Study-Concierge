# demo_run.py
"""
Robust demo runner for Everyday Ally.

Features:
- Ensures the project's src/ directory is first on sys.path so local `app` package is used.
- Changes cwd to project root.
- Prints debug info about which `app` package was imported.
- Calls planner.plan_day and prints the plan.
"""

import os
import sys
import asyncio
import json
from pprint import pprint

# --- ensure we run from project root and put src/ first on sys.path ---
ROOT = os.path.dirname(os.path.abspath(__file__))  # project root (where this file lives)
SRC = os.path.join(ROOT, "src")

# change working directory to project root (helps relative imports and file reads)
os.chdir(ROOT)

# make sure SRC is the very first entry on sys.path so local packages take precedence
if SRC in sys.path:
    # move it to index 0
    sys.path.remove(SRC)
sys.path.insert(0, SRC)

print("Working dir:", os.getcwd())
print("sys.path[0] (should be project src):", sys.path[0])

# optional: show whether an installed 'app' package exists (debug)
try:
    import importlib
    # find which module would be imported for 'app'
    spec = importlib.util.find_spec("app")
    if spec is None:
        print("No 'app' package found on sys.path (unexpected).")
    else:
        print("'app' package will be loaded from:", spec.origin or spec)
except Exception as e:
    print("Importlib check failed:", e)

# --- now import the planner singleton from our local app package ---
try:
    from app.main import planner, memory
except Exception as exc:
    print("Failed to import planner from app.main. This usually means sys.path is wrong or")
    print("there is a name collision with an installed package named 'app'.")
    raise

async def run_demo():
    user_id = "demo_user"
    availability = {
        "hours": 4,
        "topics": ["math", "algorithms"],
        "blocks": 2,
        "diet": "vegetarian",
    }

    print("\nRunning planner.plan_day(...) — this may call Gemini or use fallbacks.")
    plan = await planner.plan_day(user_id=user_id, availability=availability)

    print("\n=== Demo Plan (pretty) ===")
    pprint(plan)

    print("\n=== MemoryBank saved plans count for user:", user_id, "===")
    plans = memory.list_plans(user_id)
    print(len(plans))
    if plans:
        print("Most recent saved plan (pretty):")
        pprint(plans[-1])

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\nDemo cancelled.")
    except Exception:
        print("\nDemo failed with exception (traceback follows):")
        raise
