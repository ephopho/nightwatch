"""The Nightwatch pipeline: Collector -> Analyst -> Actioner, run in strict order by
ADK's SequentialAgent. Each stage hands off through session state (collected ->
analysis -> actions), giving a clean, decoupled, inspectable workflow rather than one
monolithic prompt.

`root_agent` is the conventional name ADK's tooling (e.g. `adk run`, `adk web`) looks
for, so it's exported here too.
"""
from google.adk.agents import SequentialAgent

from app.agents.actioner import actioner
from app.agents.analyst import analyst
from app.agents.collector import collector

nightwatch = SequentialAgent(
    name="nightwatch",
    description="Autonomous overnight watch: collect fresh signal, reason about what matters, act.",
    sub_agents=[collector, analyst, actioner],
)

# ADK entry-point convention.
root_agent = nightwatch
