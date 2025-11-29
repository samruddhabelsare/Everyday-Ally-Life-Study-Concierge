# src/app/agents/input_agent.py

"""
InputAgent - small helper to normalize text input.
"""

from typing import Dict


class InputAgent:
    """Normalizes raw UI or user text into structured dict."""

    def normalize(self, raw_input: str) -> Dict[str, str]:
        if raw_input is None:
            return {"text": ""}
        text = str(raw_input).strip()
        return {"text": text}
