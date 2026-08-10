# Building Nightwatch: an autonomous agent that does my morning triage — and actually *acts*

> *I built this project for the **All Things Agentic Hackathon** (Taskmaster category). This post describes how it works and what I learned building it.*

**TL;DR** — Nightwatch is an agent that runs on a schedule overnight, watches my wallets, contracts, and markets, uses **Gemini 3.5** to reason about what actually matters, and then **takes the routine actions** — writing a decision-ready brief, opening review issues, and sending a digest. It reasons *and* it does the chore. Code: https://github.com/ephopho/nightwatch · Live: https://nightwatch-968980032106.us-central1.run.app

---

## The friction

Every morning I'd spend 30–45 minutes doing the same thing: open a dozen wallets, contracts, and market tabs, reconstruct what changed overnight, and decide what needed action. It's tedious, it's easy to miss something, and it's *judgment plus legwork* — the exact shape of task an agent should own. So I built one.

The design constraint I set myself: **it can't just summarize.** A chatbot that writes me a paragraph hasn't done the chore. Nightwatch has to *finish* it.

## The shape of the system

Nightwatch is a Google **ADK `SequentialAgent`** with three stages, and the most important decision in the whole project is that the stages are **isolated by capability**:

```
Collector  →  Analyst  →  Actioner
(read-only)   (no tools)   (write-only)
```

- **Collector** has *only* read-only tools: fetch market quotes, fetch new on-chain transactions, search the web. It gathers signal; it can't act.
- **Analyst** is Gemini 3.5 with **zero tools**. It can only reason over what the Collector gathered. That isolation means the reasoning core physically cannot fetch or mutate anything — it just judges materiality and assigns each item a severity and a confidence score, as JSON.
- **Actioner** holds the *only* write-capable tools, and it's gated on a confidence threshold: high-confidence items trigger autonomous actions; everything else is written into the brief for human review.

Each stage hands off through session state (`collected → analysis → actions`), so the pipeline is decoupled and inspectable rather than one monolithic mega-prompt. This separation turned out to be the single biggest lever for making the system safe, debuggable, and easy to extend.

```python
nightwatch = SequentialAgent(
    name="nightwatch",
    sub_agents=[collector, analyst, actioner],
)
```

## The Google Cloud backbone

The "autonomous, overnight, no human" part is real infrastructure, not a cron on my laptop:

- **Cloud Scheduler → Pub/Sub → Cloud Run** fires the nightly run.
- **Cloud Run** hosts a small FastAPI app (`/health`, a public dashboard at `/`, and the token-gated `/run` and `/pubsub/push`).
- **Firestore** holds three things: *watermarks* so each run only processes genuinely new activity, a rolling *situation memory* so each run has cross-session context, and the *briefs* the dashboard renders.
- **Secret Manager** stores the run-trigger token and the optional integration secrets.
- **Gemini 3.5** runs on **Vertex AI**; the `web_search` tool uses the **GenAI SDK** with **Google Search grounding**, so news context comes back with real citations instead of hallucinations.

## Three things I learned the hard way

**1. Gemini 3.x on Vertex is `global`-endpoint-only.** I probed `us-central1` for `gemini-3.5-*` and got 404 on every id and nearly concluded 3.5 wasn't available yet. It is — Vertex serves 3.x models *only* from the `global` location. Regional endpoints even *list* the model ids but 404 on generate. The fix was one env var: point Gemini at `global` while Cloud Run and Firestore stay regional (Firestore doesn't care — it keys off the project).

**2. Tool isolation beats a smarter prompt.** My first instinct was one clever agent with all the tools. Splitting it into read-only Collector / tool-less Analyst / write-scoped Actioner made everything better: the security story writes itself (write access lives in exactly one place), failures are localized, and I can reason about each stage independently.

**3. Fail *soft*, always.** The write tools degrade to clean no-ops when their integration isn't configured — so a live run never crashes mid-demo because a token is missing. On API errors they surface the provider's own message (`Bad credentials`, `chat not found`) instead of an opaque status code. And a bug worth a chuckle: `openssl rand -hex 32 | tr -d '\n'` on Windows left a stray carriage return baked into my Secret Manager token, silently 401-ing every request until I stripped `\r` *and* `\n`.

## Proof it runs

The runner logs the entire reasoning chain to Cloud Logging, so a single `POST /run` on Cloud Run streams exactly this:

```
[nightwatch] cycle ... start | model=gemini-3.5-flash location=global | watch=BTC, ETH, SOL
[nightwatch] [collector] CALL fetch_market(...)  / RESP ...
[nightwatch] [collector] CALL web_search(...)    / RESP ...(grounded citations)
[nightwatch] [analyst]  FINAL {"items":[{"severity":"high","confidence":0.95,...}]}
[nightwatch] [actioner] CALL write_brief(...)    / RESP {'ok': True, 'brief_id': '...'}
[nightwatch] cycle ... done
```

Collector → Analyst → Actioner, end to end, on real Google Cloud infrastructure — and out the other side comes a decision-ready brief, with the routine follow-ups already done.

## What's next

OIDC auth on the Pub/Sub path, richer on-chain analytics, more watchlist source types, and pluggable action targets beyond GitHub and Telegram.

If you want to poke at it, the repo has full spin-up and deploy instructions: **https://github.com/ephopho/nightwatch**

---

*Built for the All Things Agentic Hackathon. Gemini 3.5 · Google ADK · Cloud Run · Firestore · Pub/Sub.*
