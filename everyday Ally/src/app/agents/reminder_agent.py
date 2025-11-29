# src/app/agents/reminder_agent.py
"""
ReminderAgent - in-process reminder scheduler with snooze/resume.

Features:
- schedule_reminder(user_id, when_iso, message, reminder_id optional)
- list_reminders(user_id)
- cancel_reminder(user_id, reminder_id)
- snooze_reminder(user_id, reminder_id, minutes)
- background loop checks reminders every CHECK_INTERVAL seconds and "fires" them by calling a handler
- reminders are persisted in MemoryBank under key 'reminders' so they survive until process restart
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

CHECK_INTERVAL = 10  # seconds between scheduler checks (short for demo; increase in prod)

class ReminderAgent:
    def __init__(self, memory, loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        memory: an instance of your MemoryBank (must support get_user_pref and set_user_pref)
        loop: optional asyncio loop - uses current loop if None
        """
        self.memory = memory
        self.loop = loop or asyncio.get_event_loop()
        self._task = None
        # In-memory index for quick lookup: {user_id: {reminder_id: reminder_dict}}
        self._index: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._running = False
        self._start_background_loop()

    # ------------------ Storage helpers ------------------
    def _load_all(self):
        """Load reminders from memory into _index (on startup)."""
        # MemoryBank stores user prefs; we keep reminders in prefs under key 'reminders'
        # Each user's reminders is a dict keyed by reminder_id
        # Example: prefs['reminders'] = { id1: {...}, id2: {...} }
        # Grab all user_prefs and look for reminders
        # memory.user_prefs is internal; use public API if available
        # We try both: memory.saved_plans (not used) and memory.user_prefs
        try:
            # best-effort: check for attribute
            all_users = getattr(self.memory, "user_prefs", {}) or {}
            for user_id, prefs in all_users.items():
                rem = prefs.get("reminders", {})
                if isinstance(rem, dict):
                    self._index[user_id] = rem.copy()
        except Exception:
            # fallback: empty index
            self._index = {}

    def _persist_for_user(self, user_id: str):
        """Write the reminders for one user into memory prefs."""
        prefs = self.memory.get_user_pref(user_id) or {}
        prefs["reminders"] = self._index.get(user_id, {}).copy()
        self.memory.set_user_pref(user_id, prefs)

    # ------------------ Public API ------------------
    def schedule_reminder(self, user_id: str, when_iso: str, message: str, reminder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Schedule a reminder.
        - when_iso: ISO8601 time string in UTC (e.g., '2025-11-20T14:30:00Z') or local time (no Z)
        - returns the reminder dict stored
        """
        rid = reminder_id or str(uuid.uuid4())
        # parse time
        when = self._parse_time(when_iso)
        reminder = {
            "id": rid,
            "when_iso": when.astimezone(timezone.utc).isoformat(),
            "message": message,
            "user_id": user_id,
            "status": "scheduled",   # scheduled | fired | cancelled | snoozed
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._index.setdefault(user_id, {})[rid] = reminder
        self._persist_for_user(user_id)
        return reminder

    def list_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """Return list of reminders (sorted by time ascending)."""
        items = list(self._index.get(user_id, {}).values())
        try:
            items.sort(key=lambda r: r.get("when_iso", ""))
        except Exception:
            pass
        return items

    def cancel_reminder(self, user_id: str, reminder_id: str) -> bool:
        """Cancel a reminder. Returns True if removed/marked cancelled."""
        user_rem = self._index.get(user_id, {})
        r = user_rem.get(reminder_id)
        if not r:
            return False
        r["status"] = "cancelled"
        self._persist_for_user(user_id)
        return True

    def snooze_reminder(self, user_id: str, reminder_id: str, minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Snooze an existing reminder by minutes. Returns updated reminder or None."""
        user_rem = self._index.get(user_id, {})
        r = user_rem.get(reminder_id)
        if not r:
            return None
        # parse current when and add minutes
        current = self._parse_time(r["when_iso"])
        new_when = current + timedelta(minutes=minutes)
        r["when_iso"] = new_when.astimezone(timezone.utc).isoformat()
        r["status"] = "snoozed"
        self._persist_for_user(user_id)
        return r

    # ------------------ Internal runner ------------------
    def _start_background_loop(self):
        if self._running:
            return
        self._load_all()
        self._running = True
        # create background task
        try:
            # prefer create_task if loop running
            self._task = asyncio.ensure_future(self._run_loop())
        except Exception:
            # fallback: start in new thread with its own loop
            import threading
            t = threading.Thread(target=self._thread_loop, daemon=True)
            t.start()

    def _thread_loop(self):
        # runs in background thread with its own event loop
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        new_loop.run_until_complete(self._run_loop())

    async def _run_loop(self):
        """Background loop that checks for reminders and fires them."""
        try:
            while True:
                now = datetime.now(timezone.utc)
                # iterate shallow copy to avoid mutation during iteration
                for user_id, rems in list(self._index.items()):
                    for rid, reminder in list(rems.items()):
                        status = reminder.get("status")
                        if status in ("cancelled", "fired"):
                            continue
                        when = self._parse_time(reminder.get("when_iso"))
                        # if reminder due or overdue -> fire
                        if when <= now:
                            try:
                                await self._handle_fire(reminder)
                                # mark fired
                                reminder["status"] = "fired"
                                reminder["fired_at"] = datetime.now(timezone.utc).isoformat()
                                self._persist_for_user(user_id)
                            except Exception:
                                # don't bring down loop
                                reminder["status"] = "error"
                                self._persist_for_user(user_id)
                await asyncio.sleep(CHECK_INTERVAL)
        except asyncio.CancelledError:
            return
        except Exception:
            # swallow unexpected exception and keep loop alive after short delay
            await asyncio.sleep(5)
            await self._run_loop()

    async def _handle_fire(self, reminder: Dict[str, Any]):
        """
        Called when a reminder is due. For now we simply print to stdout and record in memory.
        Replace this method to integrate with real notifiers (email, push, SMS).
        """
        # example handler — print and attach 'notified' note to memory
        msg = f"[Reminder Fired] user={reminder.get('user_id')} id={reminder.get('id')} when={reminder.get('when_iso')}\n  message: {reminder.get('message')}"
        print(msg)
        # store a history entry in memory user_pref 'reminder_history'
        user_id = reminder.get("user_id")
        if user_id:
            prefs = self.memory.get_user_pref(user_id) or {}
            hist = prefs.get("reminder_history", [])
            hist.append({"id": reminder.get("id"), "when": datetime.now(timezone.utc).isoformat(), "message": reminder.get("message")})
            prefs["reminder_history"] = hist
            self.memory.set_user_pref(user_id, prefs)

    # ------------------ Utilities ------------------
    @staticmethod
    def _parse_time(when_iso: str) -> datetime:
        """
        Parse ISO time input robustly. If no timezone present, assume local and convert to UTC.
        Returns timezone-aware datetime in UTC.
        """
        if when_iso is None:
            return datetime.now(timezone.utc)
        # Try datetime.fromisoformat (py3.11+), then fallback
        try:
            dt = datetime.fromisoformat(when_iso)
            if dt.tzinfo is None:
                # assume local naive -> convert to UTC
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            # last resort: attempt common formats
            try:
                from dateutil import parser
                dt = parser.parse(when_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                return datetime.now(timezone.utc)
