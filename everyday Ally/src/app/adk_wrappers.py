# src/app/adk_wrappers.py
"""
Robust ADK wrapper for Everyday Ally.

This version is defensive about ADK API shapes. If the ADK package is present but
does not expose the expected decorators (tool/agent), the module will *not* try to
use those decorators and will fall back to the non-ADK wrapper so the app keeps running.

Goal: non-destructive, keep your app working regardless of ADK version.
"""

from typing import Any, Dict, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

adk_planner = None
ADK_AVAILABLE = False

def _run_coro_sync(coro):
    """Run coroutine in a fresh event loop and return result (safe for calling from sync context)."""
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
    except Exception:
        # fallback to trying to run on existing loop
        try:
            return asyncio.get_event_loop().run_until_complete(coro)
        except Exception as e:
            logger.exception("Failed to run coroutine synchronously: %s", e)
            raise

def ensure_adk_ready(planner=None, memory=None):
    """
    Attempt to register ADK tools/agents. This function is defensive:
    - If ADK is absent => returns False and uses fallback wrapper.
    - If ADK is present but missing decorators or expected APIs => logs and returns False (fallback).
    - If ADK is present and shape matches => registers tools & agent and returns True.
    """
    global adk_planner, ADK_AVAILABLE
    adk_planner = None
    ADK_AVAILABLE = False

    try:
        # Try to import ADK (course examples use `from google import adk`)
        from google import adk  # type: ignore
    except Exception as exc:
        logger.info("Google ADK not importable (%s). Using fallback planner wrapper.", exc)
        # fallback planner wrapper
        class _FallbackPlanner:
            def __init__(self, planner_impl):
                self._planner = planner_impl
            async def run(self, user_id: str, availability: Dict[str, Any]):
                return await self._planner.plan_day(user_id=user_id, availability=availability)
        adk_planner = _FallbackPlanner(planner)
        return False

    # ADK module imported. Check for expected API (decorators).
    has_tool = hasattr(adk, "tool")
    has_agent = hasattr(adk, "agent")
    # Some ADK variations may use a different attribute namespace; be defensive.
    if not (has_tool and has_agent):
        logger.warning("ADK module imported but missing expected decorators (tool/agent). Detected attributes: %s", [a for a in dir(adk) if a.startswith("_") is False][:80])
        # Fall back to non-ADK mode to avoid runtime errors.
        class _FallbackPlanner2:
            def __init__(self, planner_impl):
                self._planner = planner_impl
            async def run(self, user_id: str, availability: Dict[str, Any]):
                return await self._planner.plan_day(user_id=user_id, availability=availability)
        adk_planner = _FallbackPlanner2(planner)
        return False

    # If we reach here ADK seems to have the decorators. Register tools & agent.
    ADK_AVAILABLE = True
    logger.info("Google ADK decorators present. Registering ADK tools and Planner agent.")

    try:
        # Define ADK tools wrapping existing sub-agents
        @adk.tool()
        def tool_generate_study_blocks(user_id: str, availability: Dict[str, Any]):
            try:
                return _run_coro_sync(planner.study_agent.generate_study_blocks(availability))
            except Exception as e:
                logger.exception("tool_generate_study_blocks error: %s", e)
                return []

        @adk.tool()
        def tool_generate_meals(user_id: str, availability: Dict[str, Any]):
            try:
                return _run_coro_sync(planner.nutrition_agent.generate_meals(availability))
            except Exception as e:
                logger.exception("tool_generate_meals error: %s", e)
                return []

        @adk.tool()
        def tool_generate_workout(user_id: str, availability: Dict[str, Any]):
            try:
                return _run_coro_sync(planner.fitness_agent.generate_fitness_plan(availability))
            except Exception as e:
                logger.exception("tool_generate_workout error: %s", e)
                return {"workout": "30 min walk"}

        # ADK Planner agent using the tools
        @adk.agent(tools=[tool_generate_study_blocks, tool_generate_meals, tool_generate_workout])
        def planner_agent(ctx: adk.Context, user_id: str, availability: Dict[str, Any]):
            try:
                if hasattr(ctx, "call_tool"):
                    study_blocks = ctx.call_tool(tool_generate_study_blocks, user_id=user_id, availability=availability)
                    meals = ctx.call_tool(tool_generate_meals, user_id=user_id, availability=availability)
                    workout = ctx.call_tool(tool_generate_workout, user_id=user_id, availability=availability)
                else:
                    study_blocks = tool_generate_study_blocks(user_id=user_id, availability=availability)
                    meals = tool_generate_meals(user_id=user_id, availability=availability)
                    workout = tool_generate_workout(user_id=user_id, availability=availability)

                plan = {"user_id": user_id, "study_blocks": study_blocks, "meals": meals, "workout": workout}
                # attempt to store in session if available
                try:
                    if hasattr(ctx, "session") and hasattr(ctx.session, "set"):
                        ctx.session.set("last_plan", plan)
                except Exception:
                    pass
                return plan
            except Exception as e:
                logger.exception("planner_agent encountered error: %s", e)
                return _run_coro_sync(planner.plan_day(user_id=user_id, availability=availability))

        # Runner to call the ADK agent consistently
        class _ADKPlannerRunner:
            async def run(self, user_id: str, availability: Dict[str, Any]):
                try:
                    # prefer adk.run_agent if available
                    if hasattr(adk, "run_agent"):
                        return await adk.run_agent(planner_agent, user_id=user_id, availability=availability)
                    # prefer planner_agent.run if present
                    if hasattr(planner_agent, "run"):
                        return await planner_agent.run(user_id=user_id, availability=availability)
                    # fallback: call planner_agent directly
                    result = planner_agent(user_id=user_id, availability=availability)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                except Exception as e:
                    logger.exception("ADKPlannerRunner failed: %s", e)
                    return await planner.plan_day(user_id=user_id, availability=availability)

        adk_planner = _ADKPlannerRunner()
        return True

    except Exception as e:
        logger.exception("Failed to register ADK tools/agent: %s", e)
        # final safe fallback
        class _FallbackPlannerFinal:
            def __init__(self, planner_impl):
                self._planner = planner_impl
            async def run(self, user_id: str, availability: Dict[str, Any]):
                return await self._planner.plan_day(user_id=user_id, availability=availability)
        adk_planner = _FallbackPlannerFinal(planner)
        ADK_AVAILABLE = False
        return False
