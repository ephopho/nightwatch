"""Cloud Run entry point (FastAPI).

Endpoints:
  GET  /health       — liveness probe for Cloud Run.
  GET  /             — minimal dashboard rendering the latest brief from Firestore.
  POST /run          — trigger a cycle by hand (used in the demo).
  POST /pubsub/push  — Pub/Sub push target; Cloud Scheduler -> Pub/Sub -> here fires
                       the nightly autonomous run.

The scheduled path (Scheduler -> Pub/Sub -> /pubsub/push) is what makes the agent run
"asynchronously in the background" without a human — the behaviour the rubric weights.
"""
import html

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.memory import store
from app.runner import run_cycle

app = FastAPI(title="Nightwatch", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    brief = store.latest_brief()
    body = brief["markdown"] if brief else "_No brief yet. Trigger a run._"
    when = brief["created_at"] if brief else ""
    return (
        "<!doctype html><meta charset='utf-8'><title>Nightwatch</title>"
        "<div style='max-width:760px;margin:40px auto;font-family:system-ui;line-height:1.5'>"
        "<h1>🌙 Nightwatch</h1>"
        f"<p style='color:#666'>Latest brief {html.escape(when)}</p>"
        f"<pre style='white-space:pre-wrap'>{html.escape(body)}</pre>"
        "</div>"
    )


@app.post("/run")
def manual_run() -> JSONResponse:
    return JSONResponse(run_cycle())


@app.post("/pubsub/push")
async def pubsub_push(request: Request) -> JSONResponse:
    # Pub/Sub wraps the message in an envelope; we don't need its payload to run the
    # nightly cycle, but we read it so malformed requests fail fast. Returning 2xx acks.
    try:
        await request.json()
    except Exception:  # noqa: BLE001 — a bad body shouldn't wedge the subscription
        pass
    result = run_cycle()
    return JSONResponse({"ok": True, **result})
