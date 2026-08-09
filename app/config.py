"""Central, env-driven config. Nothing secret is hard-coded — Cloud Run injects env
vars (via Secret Manager for tokens). Locally, values come from a .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "nightwatch"

# --- Model / Vertex ---------------------------------------------------------
# Must be Gemini 3.5 or newer per the hackathon rules. Verify the exact model id
# available in your project/region before the demo.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-pro")
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
# ADK reads GOOGLE_GENAI_USE_VERTEXAI to route through Vertex AI vs AI Studio.
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

# --- What to watch ----------------------------------------------------------
# Comma-separated targets (wallet addresses, contract addresses, or symbols).
WATCHLIST = [w.strip() for w in os.getenv("NIGHTWATCH_WATCHLIST", "").split(",") if w.strip()]
# Items scoring at/above this confidence may trigger autonomous actions; below it,
# they go into the brief for human review (the guardrail the rubric rewards).
CONFIDENCE_THRESHOLD = float(os.getenv("NIGHTWATCH_CONFIDENCE", "0.6"))

# --- Action integrations (all optional; stubs no-op when unset) -------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")          # "owner/repo" for review issues
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Run-trigger auth -------------------------------------------------------
# When set, POST /run and /pubsub/push require this shared token (Bearer header or a
# ?token= query param). Left unset (local dev), the trigger endpoints stay open.
RUN_TOKEN = os.getenv("RUN_TOKEN", "")
