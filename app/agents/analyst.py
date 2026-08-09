"""Analyst — the reasoning core. NO tools: it can only think over what the Collector
gathered, which enforces tool isolation (it can't fetch or act). Reads `collected`
from session state, writes structured judgement to `analysis`.
"""
from google.adk.agents import LlmAgent

from app import config

analyst = LlmAgent(
    name="analyst",
    model=config.GEMINI_MODEL,
    description="Reasons over raw findings to decide what actually matters.",
    instruction=(
        "You are the Analyst. Here are the Collector's raw findings:\n\n{collected}\n\n"
        "Reason about materiality: filter noise, correlate related signals into a single "
        "story where possible (e.g. a wallet moving to an exchange + a price drop + a "
        "governance post = de-risking), and judge severity. For each item assign a "
        "confidence between 0 and 1 that it is real and material.\n\n"
        "Respond ONLY with JSON of the form:\n"
        '{"items": [{"headline": str, "severity": "low|medium|high", '
        '"confidence": float, "rationale": str, "suggested_action": str}]}'
    ),
    output_key="analysis",
)
