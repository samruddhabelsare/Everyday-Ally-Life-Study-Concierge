# src/app/ui/streamlit_app.py
import os
import streamlit as st
import requests
from datetime import datetime, timedelta

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Everyday Ally", layout="wide")

st.title("🧠 Everyday Ally — Your Daily AI Planner & Reminder Assistant")

# --------------------------------------------------------------------
# DAILY PLANNER SECTION
# --------------------------------------------------------------------
st.header("📅 Daily Planner")

col1, col2 = st.columns([2, 1])

with col1:
    user_id = st.text_input("User ID", value="demo_user")

    hours = st.number_input("Available hours today", min_value=1, max_value=24, value=4)

    topics = st.text_input("Study Topics (comma-separated)", value="math, algorithms")

    diet = st.selectbox(
        "Meal Preference",
        ["omnivore", "vegetarian", "vegan"],
        index=1
    )

    blocks = st.number_input("Number of study blocks", min_value=1, max_value=6, value=2)

with col2:
    st.write("")
    st.write("")
    if st.button("✨ Generate Daily Plan"):
        availability = {
            "hours": int(hours),
            "topics": [t.strip() for t in topics.split(",") if t.strip()],
            "diet": diet,
            "blocks": int(blocks),
        }

        payload = {"user_id": user_id, "availability": availability}

        try:
            r = requests.post(f"{API_BASE}/plan/day", json=payload, timeout=30)
            r.raise_for_status()
            resp = r.json()

            st.session_state["last_plan"] = resp.get("plan")
            st.success("Plan generated successfully!")

        except Exception as e:
            st.error(f"Failed to generate plan: {e}")

# SHOW PLAN
if "last_plan" in st.session_state:
    st.subheader("📘 Your Plan")
    st.json(st.session_state["last_plan"])


# --------------------------------------------------------------------
# REMINDERS SECTION
# --------------------------------------------------------------------
st.markdown("---")
st.header("⏰ Reminders")

rcol1, rcol2 = st.columns([2, 1])

with rcol1:
    r_user = st.text_input("Reminder User", value="demo_user", key="r_user")
    r_message = st.text_input("Message", value="Stand up and stretch", key="r_message")

    # default reminder 1 min from now
    r_when = st.text_input(
        "Reminder Time (ISO8601 UTC)",
        value=(datetime.utcnow() + timedelta(minutes=1)).replace(microsecond=0).isoformat() + "Z",
        key="r_when"
    )

    if st.button("➕ Create Reminder"):
        body = {
            "user_id": r_user,
            "when_iso": r_when,
            "message": r_message
        }

        try:
            resp = requests.post(f"{API_BASE}/reminder/create", json=body, timeout=10)
            resp.raise_for_status()
            st.success("Reminder created!")
        except Exception as e:
            st.error(f"Failed to create reminder: {e}")

with rcol2:
    if st.button("📄 List Reminders"):
        try:
            resp = requests.get(f"{API_BASE}/reminder/list/{r_user}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            reminders = data.get("reminders", [])
            st.session_state["reminders"] = reminders
        except Exception as e:
            st.error(f"Failed to load reminders: {e}")

# DISPLAY REMINDERS
reminders = st.session_state.get("reminders", [])
if reminders:
    st.subheader(f"🔔 Active Reminders for {r_user}")
    for rem in reminders:
        with st.expander(f"{rem.get('when_iso')} — {rem.get('message')}"):
            st.write(rem)

            if st.button("Snooze 5 minutes", key=f"snooze_{rem['id']}"):
                try:
                    body = {
                        "user_id": r_user,
                        "reminder_id": rem["id"],
                        "minutes": 5
                    }
                    resp = requests.post(f"{API_BASE}/reminder/snooze", json=body, timeout=10)
                    resp.raise_for_status()
                    st.success("Snoozed!")
                except Exception as e:
                    st.error(f"Snooze failed: {e}")

            if st.button("Cancel", key=f"cancel_{rem['id']}"):
                try:
                    body = {
                        "user_id": r_user,
                        "reminder_id": rem["id"]
                    }
                    resp = requests.post(f"{API_BASE}/reminder/cancel", json=body, timeout=10)
                    resp.raise_for_status()
                    st.success("Cancelled!")
                except Exception as e:
                    st.error(f"Cancel failed: {e}")

st.markdown("---")
st.caption(f"Backend: {API_BASE}")
