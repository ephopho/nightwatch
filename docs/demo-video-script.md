# 🌙 Nightwatch — 4-Minute Demo Video Script

**Category:** Taskmaster · **Models:** Gemini 3.5 + Gemma (Vertex AI) · **Runtime:** Cloud Run
**Hard rules:** ≤ 4:00, English, **unedited live run**, **visible proof the backend runs on Google Cloud.**

The script is written to score against the rubric:
- **Innovation & Operational Utility (40%)** → Beats 1–2 (the friction + the "reason *and* act" twist).
- **Architectural Discipline (30%)** → Beat 3 (decoupled stages, tool isolation, state, failure-tolerance).
- **Demo & Production Readiness (30%)** → Beats 4–5 (unedited live run + Google Cloud proof).

Target narration ≈ **560 words** (~140 wpm) to land under 4:00 with breathing room.

---

## Pre-flight checklist (do this BEFORE hitting record)

1. **Stage logging on** so the Cloud Run **Logs** tab shows the Collector→Analyst→Actioner reasoning
   chain live. *(If not yet added, ask Claude to "add stage logging" — it makes Beat 4 far stronger.)*
2. **Fetch the run token** into a terminal (don't show it on screen longer than a flash):
   ```bash
   TOKEN=$(gcloud secrets versions access latest --secret=nightwatch-run-token \
     --project=nightwatch-agent-3f9x2)
   ```
3. **Pre-open browser tabs**, logged into the `nightwatch-agent-3f9x2` project:
   - **Dashboard:** https://nightwatch-968980032106.us-central1.run.app
   - **Cloud Run** → service `nightwatch` (Revisions + Logs tabs)
   - **Vertex AI** → *Model Garden / Logs* (to show `gemini-3.5-flash` requests)
   - **Firestore** → `briefs` collection
   - **Cloud Scheduler** → `nightwatch-nightly` (shows the nightly cron)
4. Have the **architecture diagram** (README mermaid) rendered as an image on screen for Beat 3.
5. Do a **dry-run** once so the dashboard already holds a brief; you'll generate a *fresh* one on camera.
6. Screen-record at 1080p; keep the cursor deliberate; **do not cut** during the live run (Beat 4).

---

## Shot-by-shot

### Beat 1 — The friction (0:00–0:25) · *Innovation 40%*
**On screen:** You, or a fast montage: a dozen wallet/market/explorer tabs, a cluttered morning.
**Narration:**
> "Every morning I burn thirty to forty-five minutes doing the same chore — checking wallets,
> markets, and contracts, reconstructing what happened overnight, and deciding what actually needs
> action. It's tedious, it's error-prone, and it's exactly the kind of work I shouldn't be doing by hand."

### Beat 2 — What Nightwatch is + the twist (0:25–0:55) · *Innovation 40%*
**On screen:** Title card "🌙 Nightwatch — an autonomous overnight agent," then the live dashboard.
**Narration:**
> "So I built Nightwatch. It runs on a schedule overnight, watches my list, and uses **Gemini 3.5** to
> *reason* about what matters — not threshold alerts, actual judgment. Then here's the twist: it doesn't
> just report, it **acts** — writing a decision-ready brief, opening review issues, sending a digest.
> It reasons *and* it does the chore. It is not a chatbot."

### Beat 3 — Architecture (0:55–1:30) · *Architecture 30%*
**On screen:** The architecture diagram; trace the flow with the cursor as you talk.
**Narration:**
> "The engineering is deliberately decoupled. Cloud Scheduler fires Pub/Sub, which triggers Cloud Run.
> Inside runs a Google **ADK** SequentialAgent with three isolated stages. The **Collector** has only
> read-only tools — and it routes a cheap first-pass triage to the open **Gemma** model, so the expensive
> reasoning is spent only where it matters. The **Analyst** — **Gemini 3.5** — has **no tools at all**, so
> it can only reason, never act. The **Actioner** holds the only write-capable tools, gated on a confidence
> threshold. State, cross-run memory, and briefs live in **Firestore**. Read/write access is scoped per
> agent — that separation is the security story."

### Beat 4 — LIVE, UNEDITED RUN (1:30–3:05) · *Demo 30% — the "Proof of Action"*
**On screen (do NOT cut):** Split view — **left:** Cloud Run **Logs** tab; **right:** the dashboard.
Click **"Run now"**, paste the token into the prompt.
**Narration (let the logs stream underneath you):**
> "Let's run it live. I click Run now — the trigger is token-gated, so I paste the run token.
> Watch the Cloud Run logs: the **Collector** is calling its tools — live market prices from CoinGecko,
> web search **grounded through Vertex** with real citations, and a fast **Gemma** triage tagging each
> signal's materiality. Now the **Analyst** — Gemini 3.5 —
> returns structured JSON: each item with a severity and a confidence score. And the **Actioner** takes
> over: it writes the brief to Firestore, and because my GitHub and Telegram tokens aren't set here, those
> integrations **cleanly skip** instead of crashing — that's the failure-tolerance."

**On screen:** Cut to the **Firestore** `briefs` collection — a **new document appears**. Then the dashboard
**reloads** showing the fresh, severity-color-coded brief.
**Narration:**
> "There's the new brief document in Firestore — and the dashboard refreshes with the result: my overnight
> triage, done, grouped by severity, decision-ready."

### Beat 5 — Proof it's on Google Cloud (3:05–3:40) · *Demo 30%*
**On screen:** Quick tour — Cloud Run service page (**region us-central1, revision, the `.run.app` URL**),
Vertex AI logs showing **`gemini-3.5-flash`** requests, Cloud Scheduler's nightly job, Secret Manager entry.
**Narration:**
> "And it's genuinely on Google Cloud: here's the Cloud Run service and its dot-run-app URL, Vertex AI
> logs showing the Gemini 3.5 **and Gemma** calls, the nightly Cloud Scheduler job that runs this **with no
> human**, and the token secret in Secret Manager. Autonomous, scheduled, secured."

### Beat 6 — Impact & close (3:40–4:00) · *Innovation 40%*
**On screen:** Back to the finished brief on the dashboard; end card with the repo URL.
**Narration:**
> "Nightwatch turns a forty-five-minute daily chore into an overnight job that reasons about what matters
> and completes the routine follow-ups for me. It reasons, and it acts. That's Nightwatch."

---

## Recording tips
- **Stay under 4:00** — judges only evaluate the first 4 minutes. Aim for ~3:50.
- Beat 4 is the whole game (**Proof of Action**): it must be one **continuous, unedited** take showing
  logs *and* a database/UI change. Rehearse it 2–3 times.
- Flash the token for <1s; never leave it legible on a paused frame.
- Say "Gemini 3.5" and show the model id in the Vertex logs — the mandate is a **pass/fail gate**.
- Show the literal `*.run.app` URL in the address bar at least once (rules call this out explicitly).
- Upload to **YouTube or Vimeo, public** (not unlisted), and paste the link into the Devpost form.
- Add English subtitles if your audio isn't crisp.

## After the video
- Create the **Devpost submission**: text description, category = *Taskmaster*, hosted URL, repo URL,
  video link, architecture diagram.
- **Judge testing note:** put the run token (or a `curl` with it) in the Devpost *testing instructions* —
  `/run` is token-gated, and judges need it to trigger a run. The dashboard itself is public.
- **Bonus (up to +1.0):** a "how I built it" blog post, a social post with **#AllThingsAgenticHackathon**,
  and/or integrating another Google model (Gemma/Veo/Lyria).
