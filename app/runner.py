"""Runs a single Nightwatch cycle by invoking the ADK pipeline programmatically.

This is the async, background entry point — the same function is called by the manual
`/run` endpoint and by the Pub/Sub push handler, so a scheduled trigger and a demo
click go through identical code.

NOTE: the Runner/Session API is the part most likely to drift with ADK versions —
if imports or signatures fail, check https://google.github.io/adk-docs/ and adjust
here only; the agents/tools above stay the same.
"""
import asyncio
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app import config
from app.agents.pipeline import nightwatch
from app.memory import store


async def run_cycle_async() -> dict:
    session_service = InMemorySessionService()
    runner = Runner(app_name=config.APP_NAME, agent=nightwatch, session_service=session_service)

    user_id = "scheduler"
    session_id = f"cycle-{uuid.uuid4().hex[:8]}"
    await session_service.create_session(
        app_name=config.APP_NAME, user_id=user_id, session_id=session_id
    )

    watch = ", ".join(config.WATCHLIST) or "(set NIGHTWATCH_WATCHLIST)"
    memory = store.recent_memory()
    prompt = (
        f"Run tonight's watch for these targets: {watch}.\n"
        f"Recent situation memory (most recent first): {memory}"
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    return {"session_id": session_id, "summary": final_text}


def run_cycle() -> dict:
    """Synchronous wrapper for request handlers."""
    return asyncio.run(run_cycle_async())
