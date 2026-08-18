# Nightwatch — social post (hackathon bonus, +0.2)

> **Bonus rule:** post on X, LinkedIn, Instagram, or Facebook, and **include `#AllThingsAgenticHackathon`**.
> Make the post **public**. Attach the thumbnail (`docs/nightwatch-thumbnail.png`) for reach. You post it —
> I can't post on your behalf.

---

## X / Twitter (≈270 chars — trim if your account caps at 280)

```
🌙 Built Nightwatch for the #AllThingsAgenticHackathon: an autonomous agent that
does your morning triage. Watches wallets + markets overnight, reasons with
Gemini 3.5 + Gemma via Google ADK on Cloud Run, then *takes action*. It reasons
AND acts — not a chatbot.
github.com/ephopho/nightwatch
```

## LinkedIn (longer form)

```
🌙 I built Nightwatch for Google's #AllThingsAgenticHackathon.

The friction: every morning I'd spend 30–45 minutes checking wallets, contracts,
and markets, reconstructing what happened overnight, and deciding what needed
action. Tedious, error-prone, and exactly the kind of judgment-plus-legwork an
agent should own.

Nightwatch does it autonomously — and the key part: it doesn't just summarize,
it *acts*. On a nightly schedule it:
• Collects live market, on-chain, and grounded-news signal (read-only tools)
• Reasons over it with Gemini 3.5 to judge what actually matters — routing the
  cheap first-pass triage to the open Gemma model
• Takes action: writes a decision-ready brief, opens review issues, sends a
  digest — all gated on a confidence threshold

Under the hood it's a Google ADK SequentialAgent with three capability-isolated
stages (read-only Collector → tool-less Analyst → write-scoped Actioner), running
on Cloud Run, state in Firestore, fired nightly by Cloud Scheduler + Pub/Sub.
Two Google models, one clean pipeline.

It reasons AND acts — not a chatbot.

Code + live demo 👉 github.com/ephopho/nightwatch

#AllThingsAgenticHackathon #GoogleCloud #Gemini #AIagents #Vertex
```

---

## Posting tips
- **The hashtag `#AllThingsAgenticHackathon` is mandatory** for the bonus — keep it exactly.
- Attach **`docs/nightwatch-thumbnail.png`** (or a 5–10s screen capture of the live run) — media lifts reach.
- Set the post to **Public** (LinkedIn: "Anyone"; X: public account).
- Optional: tag **@GoogleCloud** and link the demo `https://nightwatch-968980032106.us-central1.run.app`.
- Post once the video is up so you can link it — but the hashtag + repo link already qualify.
