"""Collector — gathers NEW raw signal for the watchlist. Read-only tools only.

Writes its findings into shared session state under `collected` (via output_key),
which the Analyst reads next. This state hand-off is how ADK's SequentialAgent keeps
the stages decoupled.
"""
from google.adk.agents import LlmAgent

from app import config
from app.tools.collect import fetch_market, fetch_onchain, web_search

collector = LlmAgent(
    name="collector",
    model=config.GEMINI_MODEL,
    description="Gathers fresh on-chain, market, and news signal for the watchlist.",
    instruction=(
        "You are the Collector in an autonomous overnight watch pipeline. "
        "Use your tools to gather the latest on-chain activity, market quotes, and "
        "relevant news for the user's watchlist. Only report genuinely fresh/notable "
        "signal — skip noise. Return a compact, structured summary of the raw findings; "
        "do not analyze or draw conclusions (that's the Analyst's job)."
    ),
    tools=[fetch_onchain, fetch_market, web_search],
    output_key="collected",
)
