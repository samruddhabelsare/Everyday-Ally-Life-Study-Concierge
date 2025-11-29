# src/app/llm/llm_client.py
"""
GenAI client wrapper tailored to google.generativeai (GenerativeModel).
Provides async helper `generate_text` returning {'raw':..., 'text':..., 'json': ... (if parseable)}.
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# Try import the official SDK
try:
    import google.generativeai as genai  # type: ignore
    SDK_AVAILABLE = True
except Exception as e:
    genai = None
    SDK_AVAILABLE = False
    logger.warning("google.generativeai import failed: %s", e)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
API_KEY = os.getenv("GEMINI_API_KEY")  # optional if using ADC via GOOGLE_APPLICATION_CREDENTIALS

# If SDK available, configure it if an API key is present
if SDK_AVAILABLE:
    try:
        # configure() is supported by google-generativeai
        if API_KEY:
            genai.configure(api_key=API_KEY)
        # If ADC is used, GOOGLE_APPLICATION_CREDENTIALS should be set and no api_key required
    except Exception as e:
        logger.warning("Failed to configure google.generativeai: %s", e)


def _extract_text_from_response(resp: Any) -> str:
    """Try common response shapes to obtain textual content."""
    if resp is None:
        return ""
    # Some SDK returns an object with .text or .candidates
    try:
        # If it's a mapping/dict-like
        if isinstance(resp, dict):
            if "candidates" in resp and len(resp["candidates"]) > 0:
                c = resp["candidates"][0]
                if isinstance(c, dict) and "content" in c:
                    return c["content"]
                if isinstance(c, dict) and "text" in c:
                    return c["text"]
            if "output" in resp and isinstance(resp["output"], str):
                return resp["output"]
            if "text" in resp and isinstance(resp["text"], str):
                return resp["text"]
        # Object-like
        if hasattr(resp, "text"):
            return getattr(resp, "text")
        if hasattr(resp, "candidates"):
            candidates = getattr(resp, "candidates")
            if isinstance(candidates, (list, tuple)) and candidates:
                first = candidates[0]
                if hasattr(first, "content"):
                    return getattr(first, "content")
                if isinstance(first, dict) and "content" in first:
                    return first["content"]
    except Exception:
        pass
    # Fallback
    try:
        return str(resp)
    except Exception:
        return ""

def _parse_json_if_possible(text: str) -> Optional[Any]:
    """Try to extract JSON from text; if text contains extra commentary, attempt to find first JSON block."""
    if not text:
        return None
    text = text.strip()
    # quick direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # attempt to find a JSON substring (first { ... } or [ ... ])
    start = None
    for i, ch in enumerate(text):
        if ch == "{" or ch == "[":
            start = i
            break
    if start is None:
        return None
    # find last matching bracket from end
    for j in range(len(text)-1, start-1, -1):
        if (text[j] == "}" and text[start] == "{") or (text[j] == "]" and text[start] == "["):
            candidate = text[start:j+1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    return None

def _fallback_response() -> Dict[str, Any]:
    fallback_json = {
        "note": "fallback",
        "meals": [
            {"meal": "Fallback Breakfast", "desc": "Toast + eggs", "cal": 350},
            {"meal": "Fallback Lunch", "desc": "Rice + dal", "cal": 600},
        ],
        "study_blocks": [
            {"title": "Fallback Block 1", "duration_min": 45, "goal": "Review key topics"},
            {"title": "Fallback Block 2", "duration_min": 45, "goal": "Practice questions"},
        ],
        "workout": {"workout": "30 min walk"},
    }
    return {"raw": None, "text": json.dumps(fallback_json), "json": fallback_json}


def generate_text_sync(prompt: str, temperature: float = 0.2, max_output_tokens: int = 512, **kwargs) -> Dict[str, Any]:
    """
    Blocking synchronous call. Uses google.generativeai.GenerativeModel when available.
    Returns {'raw': raw_response, 'text': extracted_text, 'json': parsed_json (if parseable)}
    """
    if not SDK_AVAILABLE:
        logger.warning("GenAI SDK not available; returning fallback.")
        return _fallback_response()

    try:
        # Preferred explicit path for google.generativeai: GenerativeModel
        if hasattr(genai, "GenerativeModel"):
            model = genai.GenerativeModel(MODEL)
            # Some SDK variants accept generate_content(prompt=...), others accept a single arg
            try:
                resp = model.generate_content(prompt)
            except TypeError:
                # fallback try different kwarg names
                resp = model.generate_content(text=prompt)
            text = _extract_text_from_response(resp)
            parsed = _parse_json_if_possible(text)
            result = {"raw": resp, "text": text}
            if parsed is not None:
                result["json"] = parsed
            return result

        # If the SDK exposes a client-level API (older/newer variants), try that:
        if hasattr(genai, "Client"):
            client = genai.Client()
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                resp = client.models.generate_content(model=MODEL, text=prompt, max_output_tokens=max_output_tokens)
                text = _extract_text_from_response(resp)
                parsed = _parse_json_if_possible(text)
                result = {"raw": resp, "text": text}
                if parsed is not None:
                    result["json"] = parsed
                return result

        # last resort: try genai.models.generate_content
        if hasattr(genai, "models") and hasattr(genai.models, "generate_content"):
            resp = genai.models.generate_content(model=MODEL, contents=[{"type":"text","text":prompt}], max_output_tokens=max_output_tokens)
            text = _extract_text_from_response(resp)
            parsed = _parse_json_if_possible(text)
            result = {"raw": resp, "text": text}
            if parsed is not None:
                result["json"] = parsed
            return result

    except Exception as e:
        logger.exception("GenAI SDK call failed: %s", e)
        # fall back
        return _fallback_response()

    # if none matched
    logger.error("Unsupported GenAI SDK call shape. Returning fallback.")
    return _fallback_response()


async def generate_text(prompt: str, temperature: float = 0.2, max_output_tokens: int = 512, **kwargs) -> Dict[str, Any]:
    """
    Async wrapper that runs the blocking `generate_text_sync` in a thread.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_text_sync, prompt, temperature, max_output_tokens, **kwargs)
