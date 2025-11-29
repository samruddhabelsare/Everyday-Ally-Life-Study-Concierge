# src/app/memory/memory_bank.py

class MemoryBank:
    """Simple in-memory storage for user preferences & plans."""

    def __init__(self):
        self.user_prefs = {}
        self.saved_plans = {}

    def save_plan(self, user_id: str, plan: dict):
        self.saved_plans.setdefault(user_id, []).append(plan)

    def list_plans(self, user_id: str):
        return self.saved_plans.get(user_id, [])

    def set_user_pref(self, user_id: str, pref: dict):
        self.user_prefs[user_id] = pref

    def get_user_pref(self, user_id: str):
        return self.user_prefs.get(user_id, {})
