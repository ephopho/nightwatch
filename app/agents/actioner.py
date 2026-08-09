"""Actioner — turns the Analyst's judgement into real actions (the Taskmaster twist).

Holds the only write-capable tools. Instruction encodes the confidence gate: high-
confidence items may trigger autonomous actions; low-confidence ones are recorded in
the brief for human review instead of acted on. Reads `analysis` from session state.
"""
from google.adk.agents import LlmAgent

from app import config
from app.tools.act import open_review_issue, send_digest, write_brief

actioner = LlmAgent(
    name="actioner",
    model=config.GEMINI_MODEL,
    description="Completes the chore: writes the brief, opens review issues, sends the digest.",
    instruction=(
        "You are the Actioner. Here is the Analyst's assessment:\n\n{analysis}\n\n"
        f"The confidence threshold is {config.CONFIDENCE_THRESHOLD}. Do the following, in order:\n"
        "1. Always call `write_brief` with a clear, decision-ready Markdown brief that "
        "covers every item, grouped by severity, and explicitly lists low-confidence "
        "items under a 'Needs review' heading.\n"
        "2. For each HIGH-severity item at or above the confidence threshold, call "
        "`open_review_issue` with a focused title and body.\n"
        "3. Call `send_digest` once with a 3-5 line summary of what needs attention.\n"
        "Never act on items below the confidence threshold beyond noting them in the brief. "
        "After acting, reply with a one-line summary of what you did."
    ),
    tools=[write_brief, open_review_issue, send_digest],
    output_key="actions",
)
