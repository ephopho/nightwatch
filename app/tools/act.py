"""Write/action tools for the Actioner agent — the "Taskmaster" payoff: the agent
doesn't just report, it *does* things. These are deliberately kept separate from the
read-only collect tools so write access is scoped to exactly one agent.

`write_brief` always persists (it powers the dashboard). `open_review_issue` and
`send_digest` degrade gracefully to a no-op when their integration isn't configured,
so the pipeline never crashes mid-run in a demo.
"""
import requests

from app import config
from app.memory import store


def write_brief(markdown: str) -> dict:
    """Persist the decision-ready brief (Markdown) so the dashboard can render it.

    Args:
        markdown: the full brief in Markdown.

    Returns:
        A dict with the saved brief id.
    """
    brief_id = store.save_brief(markdown)
    store.append_memory(markdown[:500])  # feed a snippet into cross-run memory
    return {"ok": True, "brief_id": brief_id}


def open_review_issue(title: str, body: str) -> dict:
    """Open a GitHub issue for an item that needs human review.

    Args:
        title: issue title.
        body: issue body (Markdown).

    Returns:
        A dict with the created issue URL, or a skipped flag if GitHub isn't configured.
    """
    if not (config.GITHUB_TOKEN and config.GITHUB_REPO):
        return {"ok": False, "skipped": "GITHUB_TOKEN/GITHUB_REPO not set"}
    resp = requests.post(
        f"https://api.github.com/repos/{config.GITHUB_REPO}/issues",
        headers={"Authorization": f"Bearer {config.GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body, "labels": ["nightwatch"]},
        timeout=20,
    )
    if resp.status_code >= 300:
        return {"ok": False, "error": f"github {resp.status_code}"}
    return {"ok": True, "url": resp.json().get("html_url")}


def send_digest(text: str) -> dict:
    """Send a concise digest to the operator via Telegram.

    Args:
        text: the digest message.

    Returns:
        A dict flagging whether it was sent or skipped.
    """
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return {"ok": False, "skipped": "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set"}
    resp = requests.post(
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
        timeout=20,
    )
    return {"ok": resp.ok}
