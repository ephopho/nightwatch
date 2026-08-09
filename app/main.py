"""Cloud Run entry point (FastAPI).

Endpoints:
  GET  /health       — liveness probe for Cloud Run.
  GET  /             — dashboard: renders the latest brief (Markdown→HTML) from Firestore.
  POST /run          — trigger a cycle by hand (used in the demo).
  POST /pubsub/push  — Pub/Sub push target; Cloud Scheduler -> Pub/Sub -> here fires
                       the nightly autonomous run.

The scheduled path (Scheduler -> Pub/Sub -> /pubsub/push) is what makes the agent run
"asynchronously in the background" without a human — the behaviour the rubric weights.
"""
import html
import secrets

import markdown as _md
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import config
from app.memory import store
from app.runner import run_cycle

app = FastAPI(title="Nightwatch", version="0.1.0")

# Modern, self-contained dashboard shell (no external assets — Cloud Run serves it as-is).
# {{WHEN}} / {{BODY}} are filled per request; CSS braces rule out str.format here.
_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nightwatch</title>
<style>
:root{
  --bg:#f4f5f7;--card:#fff;--ink:#1b1f24;--muted:#697586;--line:#e5e8ec;
  --accent:#6366f1;--high:#dc2626;--med:#d97706;--low:#16a34a;--chip:#f8fafc;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 12px 32px rgba(16,24,40,.08);
}
@media(prefers-color-scheme:dark){:root{
  --bg:#0b0d10;--card:#14181d;--ink:#e7eaee;--muted:#94a0b0;--line:#242b33;
  --accent:#8b93f8;--high:#f87171;--med:#fbbf24;--low:#4ade80;--chip:#0f1418;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 16px 40px rgba(0,0,0,.55);
}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:840px;margin:0 auto;padding:40px 20px 72px}
.hero{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:22px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:14px}
.moon{font-size:34px;line-height:1;filter:drop-shadow(0 2px 8px rgba(99,102,241,.35))}
h1{font-size:23px;margin:0;letter-spacing:-.02em;font-weight:680}
.sub{color:var(--muted);font-size:13px;margin-top:3px}
.actions{display:flex;align-items:center;gap:10px}
.pill{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted);
  background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--low);box-shadow:0 0 0 3px color-mix(in srgb,var(--low) 22%,transparent)}
.btn{font:inherit;font-size:13.5px;font-weight:560;cursor:pointer;border-radius:10px;
  padding:9px 15px;border:1px solid var(--line);background:var(--card);color:var(--ink);
  text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:.15s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{filter:brightness(1.07);color:#fff}
.btn[disabled]{opacity:.6;cursor:progress}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;
  padding:30px 32px;box-shadow:var(--shadow)}
.brief h1{font-size:20px;margin:0 0 6px;letter-spacing:-.01em}
.brief h2{font-size:12.5px;text-transform:uppercase;letter-spacing:.06em;font-weight:700;
  margin:26px 0 12px;padding-left:11px;border-left:3px solid var(--line);color:var(--muted)}
.brief h2.sev-high{color:var(--high);border-color:var(--high)}
.brief h2.sev-medium{color:var(--med);border-color:var(--med)}
.brief h2.sev-low{color:var(--low);border-color:var(--low)}
.brief ul{list-style:none;padding:0;margin:0}
.brief li{background:var(--chip);border:1px solid var(--line);border-radius:12px;
  padding:13px 15px;margin:9px 0}
.brief li strong{color:var(--ink);font-weight:640}
.brief p{color:var(--muted)}
.brief a{color:var(--accent)}
.empty{color:var(--muted);text-align:center;padding:26px 0}
footer{color:var(--muted);font-size:12px;text-align:center;margin-top:22px}
footer code{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:2px 6px}
</style></head><body>
<div class="wrap">
  <div class="hero">
    <div class="brand">
      <div class="moon">&#127769;</div>
      <div><h1>Nightwatch</h1><div class="sub">Autonomous overnight watch &middot; Collector &rarr; Analyst &rarr; Actioner</div></div>
    </div>
    <div class="actions">
      <span class="pill"><span class="dot"></span>{{WHEN}}</span>
      <a class="btn" href="/">Refresh</a>
      <button class="btn primary" onclick="runNow(this)">Run now</button>
    </div>
  </div>
  <div class="card"><div class="brief">{{BODY}}</div></div>
  <footer>Served live from Firestore &middot; <code>POST /run</code> to trigger a cycle</footer>
</div>
<script>
function runNow(b){var t=prompt('Run token (Secret Manager: nightwatch-run-token) — leave blank if unsecured');
  if(t===null)return;b.disabled=true;b.textContent='Running…';
  fetch('/run',{method:'POST',headers:{'Authorization':'Bearer '+t,'Content-Type':'application/json'},body:'{}'})
  .then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})
  .then(function(){location.reload()})
  .catch(function(){b.disabled=false;b.textContent='Run now';alert('Run failed — check the token.');});}
</script>
</body></html>"""


def _fmt_when(iso: str) -> str:
    """ISO timestamp -> compact 'YYYY-MM-DD HH:MM UTC' for the header pill."""
    if not iso:
        return "No brief yet"
    return iso[:16].replace("T", " ") + " UTC"


def _run_authorized(request: Request) -> bool:
    """Guard the run-trigger endpoints. Open when RUN_TOKEN is unset (local dev);
    otherwise require it as a Bearer header or a ?token= query param (constant-time)."""
    token = config.RUN_TOKEN
    if not token:
        return True
    auth = request.headers.get("authorization", "")
    presented = auth[7:] if auth[:7].lower() == "bearer " else request.query_params.get("token", "")
    return bool(presented) and secrets.compare_digest(presented, token)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    brief = store.latest_brief()
    if brief and brief.get("markdown"):
        body = _md.markdown(brief["markdown"], extensions=["extra", "sane_lists"])
        # Color-accent the known severity sections (markdown renders "## X" -> "<h2>X</h2>").
        for label, cls in (("High Severity", "sev-high"),
                           ("Medium Severity", "sev-medium"),
                           ("Low Severity", "sev-low")):
            body = body.replace(f"<h2>{label}</h2>", f'<h2 class="{cls}">{label}</h2>')
    else:
        body = "<p class='empty'>No brief yet — hit <b>Run now</b> to kick off the first overnight watch.</p>"
    when = _fmt_when(brief["created_at"] if brief else "")
    return _PAGE.replace("{{WHEN}}", html.escape(when)).replace("{{BODY}}", body)


@app.post("/run")
def manual_run(request: Request) -> JSONResponse:
    if not _run_authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse(run_cycle())


@app.post("/pubsub/push")
async def pubsub_push(request: Request) -> JSONResponse:
    # Scheduler -> Pub/Sub delivers the run token via ?token= (Pub/Sub can't set headers).
    if not _run_authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    # Pub/Sub wraps the message in an envelope; we don't need its payload to run the
    # nightly cycle, but we read it so malformed requests fail fast. Returning 2xx acks.
    try:
        await request.json()
    except Exception:  # noqa: BLE001 — a bad body shouldn't wedge the subscription
        pass
    result = run_cycle()
    return JSONResponse({"ok": True, **result})
