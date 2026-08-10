# Nightwatch — Devpost submission text

> Category: **Taskmaster** · Copy the sections below into the Devpost form.
> **Repo:** https://github.com/ephopho/nightwatch · **Live:** https://nightwatch-968980032106.us-central1.run.app

---

## Elevator pitch (≤ 200 chars)
An autonomous overnight agent that does your morning triage for you — it watches your wallets, contracts, and markets, reasons about what matters with Gemini 3.5, and takes the routine actions.

---

## Inspiration
Every morning I burned 30–45 minutes on the same chore: checking a dozen wallets, contracts, and markets, reconstructing what happened overnight, and deciding what actually needed action. It's tedious, error-prone, and exactly the kind of judgment-plus-legwork task that should run itself. That's the "Bring Your Own Friction" I set out to eliminate.

## What it does
**Nightwatch is an agent that reasons *and* acts — not a chatbot.** On a nightly schedule it:
1. **Collects** fresh signal for your watchlist — live market quotes, new on-chain transactions, and grounded news — using read-only tools.
2. **Reasons** over that signal with **Gemini 3.5**, filtering noise, correlating related events into a single story, and assigning each item a severity and a confidence score.
3. **Acts** on its judgment: it writes a decision-ready Markdown **brief** to Firestore (rendered on a live dashboard), opens **GitHub review issues** for high-confidence high-severity items, and sends a **Telegram digest** — all gated on a confidence threshold, so low-confidence items are surfaced for human review instead of acted on.

It runs autonomously in the background with no human in the loop, and hands back a brief with the routine follow-ups already done.

## How we built it
A Google **ADK `SequentialAgent`** with three deliberately isolated stages, decoupled through session state:
- **Collector** (`LlmAgent`) — read-only tools only: `fetch_market`, `fetch_onchain`, `web_search`.
- **Analyst** (`LlmAgent`, Gemini 3.5) — **no tools at all**, so it can only reason, never fetch or act. Emits structured JSON.
- **Actioner** (`LlmAgent`) — holds the *only* write-capable tools (`write_brief`, `open_review_issue`, `send_digest`), scoped to exactly one agent.

**Google Cloud (five services):** **Cloud Run** hosts a FastAPI app; **Cloud Scheduler → Pub/Sub → `/pubsub/push`** fires the nightly autonomous run; **Firestore** stores watermarks (so each run only processes *new* activity), cross-run "situation memory," and briefs; **Secret Manager** holds the run-trigger token and integration secrets. **Gemini 3.5** runs on **Vertex AI**, and `web_search` uses the **GenAI SDK** with **Google Search grounding** for cited, real-time news.

**Data sources:** CoinGecko (`/simple/price`) for market quotes; the blockchain.com explorer gateway for on-chain transactions (ETH/BTC), deduped via Firestore watermarks; Google Search grounding (via Vertex) for news context with source citations.

**Production hardening:** the trigger endpoints (`POST /run`, `/pubsub/push`) are token-gated via Secret Manager while the dashboard stays public; write tools degrade to clean no-ops when unconfigured so a run never crashes mid-demo; and the runner logs the full Collector→Analyst→Actioner reasoning chain to Cloud Logging.

## Challenges we ran into
- **Gemini 3.x on Vertex is `global`-endpoint only.** Regional endpoints (e.g. `us-central1`) *list* the 3.x model ids but return 404 on generate — a region-only probe wrongly concludes 3.5 doesn't exist. Pointing Vertex at the `global` location fixed it, while Cloud Run and Firestore stay regional.
- **Tool isolation vs. capability.** Giving the Analyst zero tools (pure reasoning) and scoping all write access to a single Actioner made the system both safer and easier to reason about.
- **A CRLF token bug.** `openssl rand -hex 32 | tr -d '\n'` on Windows left a stray carriage return in the Secret Manager token, silently breaking auth — a good reminder to strip `\r` *and* `\n`.

## Accomplishments we're proud of
A genuinely autonomous, deployed agent that completes a real multi-step chore end-to-end on Google Cloud — with a clean, decoupled, failure-tolerant architecture and a verifiable live reasoning-chain trace, not just an API call wrapped in a prompt.

## What we learned
Decoupling agents by capability (read-only Collector, tool-less Analyst, write-scoped Actioner) is the single biggest lever for a robust, secure, maintainable agentic system — and grounding the model in live tools keeps its judgment tied to reality.

## What's next
An OIDC-authenticated Pub/Sub path, richer on-chain analytics, more watchlist source types, and pluggable action targets beyond GitHub/Telegram.

## Built with
`python` · `google-adk` · `google-genai` · `gemini-3.5` · `vertex-ai` · `cloud-run` · `firestore` · `pub-sub` · `cloud-scheduler` · `secret-manager` · `fastapi` · `uvicorn` · `coingecko` · `google-search-grounding`

---

## Testing instructions (for judges)
The dashboard is public and shows the latest brief:
- **Dashboard:** https://nightwatch-968980032106.us-central1.run.app

Triggering a run is token-gated (to prevent public abuse of the paid pipeline). To run it live:
```bash
TOKEN=$(gcloud secrets versions access latest --secret=nightwatch-run-token \
  --project=nightwatch-agent-3f9x2)
curl -X POST "https://nightwatch-968980032106.us-central1.run.app/run" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
```
*(Judges: the run token is provided in the private testing-instructions field. The dashboard's "Run now" button also prompts for it.)* A cycle takes ~2–3 minutes and then the dashboard refreshes with a new brief. Full spin-up and deploy steps are in the repo `README.md`.
