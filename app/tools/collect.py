"""Read-only tools for the Collector agent.

ADK turns a plain typed+documented function into a tool: the name, type hints, and
docstring become the schema the model sees — so keep the docstrings crisp.

All three are now LIVE: `fetch_market` (CoinGecko), `fetch_onchain` (blockchain.com's
explorer gateway), and `web_search` (a Gemini call with the Google Search tool, so news
context is grounded in real pages with citations). On-chain uses Firestore watermarks so
each run only surfaces genuinely NEW transactions (seeds silently on first sighting).
"""
import re

import requests
from google import genai
from google.genai import types

from app import config
from app.memory import store

# --- Market (CoinGecko) -----------------------------------------------------
_COINGECKO = "https://api.coingecko.com/api/v3/simple/price"
_SYMBOL_TO_ID = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BCH": "bitcoin-cash",
    "USDT": "tether", "USDC": "usd-coin", "BNB": "binancecoin", "XRP": "ripple",
    "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2", "LINK": "chainlink",
}


def fetch_market(symbols: str) -> dict:
    """Fetch current USD price and 24h change for the given market symbols.

    Args:
        symbols: comma-separated tickers, e.g. "BTC,ETH,SOL".

    Returns:
        A dict mapping each symbol to {usd, change_24h}, plus any unknown symbols.
    """
    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    ids = {_SYMBOL_TO_ID[s]: s for s in wanted if s in _SYMBOL_TO_ID}
    unknown = [s for s in wanted if s not in _SYMBOL_TO_ID]
    quotes: dict[str, dict] = {}
    if ids:
        try:
            resp = requests.get(
                _COINGECKO,
                params={"ids": ",".join(ids), "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=20,
            )
            data = resp.json() if resp.ok else {}
            for cg_id, payload in data.items():
                quotes[ids[cg_id]] = {
                    "usd": payload.get("usd"),
                    "change_24h": payload.get("usd_24h_change"),
                }
        except requests.RequestException as exc:
            return {"quotes": quotes, "error": str(exc), "source": "market"}
    return {"quotes": quotes, "unknown_symbols": unknown, "source": "market"}


# --- On-chain (blockchain.com Explorer Gateway) -----------------------------
_EXPLORER = "https://api.blockchain.info/explorer-gateway-kt"


def _classify(target: str) -> str | None:
    """Best-effort chain guess from an address shape."""
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", target):
        return "eth"
    if re.fullmatch(r"(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,59}", target):
        return "btc"
    return None


def _address_tx_ids(chain: str, address: str) -> list[str]:
    """Newest-first transaction id strings for an address, or [] on failure."""
    if chain == "eth":
        path, body, key = "/eth/address", {"address": address, "network": "mainnet"}, "hash"
    else:  # btc / bch
        path, body, key = f"/{chain}/address/transactions", {"address": address}, "txId"
    try:
        resp = requests.post(f"{_EXPLORER}{path}", json=body, timeout=25)
        if not resp.ok:
            return []
        txs = resp.json().get("transactions", [])
        return [str(t[key]) for t in txs if t.get(key)]
    except requests.RequestException:
        return []


def fetch_onchain(targets: str) -> dict:
    """Fetch NEW on-chain transactions for the given wallet/contract addresses.

    Uses a per-address watermark so only transactions seen since the last run are
    returned; the first time an address is seen it is seeded silently (no events).

    Args:
        targets: comma-separated wallet/contract addresses (ETH 0x…, or BTC).

    Returns:
        A dict with an `events` list of {target, chain, new_tx_ids, count}.
    """
    events = []
    skipped = []
    for raw in targets.split(","):
        target = raw.strip()
        if not target:
            continue
        chain = _classify(target)
        if chain is None:
            skipped.append(target)  # likely a symbol, not an address — fetch_market handles it
            continue

        ids = _address_tx_ids(chain, target)
        if not ids:
            continue
        wm_key = f"onchain:{chain}:{target}"
        last = store.get_watermark(wm_key)
        newest = ids[0]

        if last is None:
            store.set_watermark(wm_key, newest)  # seed, don't fire on history
            continue

        new_ids = []
        for tx_id in ids:
            if tx_id == last:
                break
            new_ids.append(tx_id)
        if new_ids:
            store.set_watermark(wm_key, newest)
            events.append({"target": target, "chain": chain, "new_tx_ids": new_ids, "count": len(new_ids)})

    return {"events": events, "skipped": skipped, "source": "onchain"}


# --- Web search (Gemini + Google Search grounding) --------------------------
_genai_client = None


def _genai() -> "genai.Client":
    """Lazily build a google-genai client (Vertex AI when configured, else API key)."""
    global _genai_client
    if _genai_client is None:
        if str(config.USE_VERTEX).upper() in ("1", "TRUE", "YES", "Y"):
            _genai_client = genai.Client(
                vertexai=True,
                project=config.GCP_PROJECT or None,
                location=config.GCP_LOCATION or None,
            )
        else:
            _genai_client = genai.Client()  # reads GOOGLE_API_KEY
    return _genai_client


def web_search(query: str) -> dict:
    """Search the web for recent news/context relevant to the query (grounding).

    Runs a Gemini call with the Google Search tool, so the answer is grounded in live
    web pages rather than the model's memory, then returns the grounded summary and the
    source citations behind it.

    Args:
        query: what to look up, e.g. "Lido governance vote August 2026".

    Returns:
        A dict with a grounded `summary`, a `results` list of {title, url, snippet},
        and the `queries` the model actually searched.
    """
    try:
        resp = _genai().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=(
                "Find recent, notable news relevant to this watch query and summarize "
                f"what changed in roughly the last day. Be concise and factual.\n\nQuery: {query}"
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
    except Exception as exc:  # noqa: BLE001 — a search failure must not wedge the run
        return {"results": [], "summary": "", "error": str(exc), "source": "web_search"}

    candidate = (resp.candidates or [None])[0]
    meta = getattr(candidate, "grounding_metadata", None)

    results = []
    for chunk in getattr(meta, "grounding_chunks", None) or []:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None)
        if uri:
            results.append({"title": getattr(web, "title", "") or "", "url": uri, "snippet": ""})

    # Attach the grounded sentence(s) each source supports as that source's snippet.
    for support in getattr(meta, "grounding_supports", None) or []:
        text = getattr(getattr(support, "segment", None), "text", "") or ""
        for idx in getattr(support, "grounding_chunk_indices", None) or []:
            if 0 <= idx < len(results) and not results[idx]["snippet"]:
                results[idx]["snippet"] = text

    try:
        summary = (resp.text or "").strip()
    except Exception:  # noqa: BLE001 — .text can raise on non-text finishes
        summary = ""

    return {
        "results": results,
        "summary": summary,
        "queries": list(getattr(meta, "web_search_queries", None) or []),
        "source": "web_search",
    }


# --- Fast triage (open Gemma model) -----------------------------------------
_LEVEL_RE = re.compile(r"\s*(\d+)\s*[:.\-]\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)


def gemma_triage(items: str) -> dict:
    """Fast first-pass materiality triage using the open **Gemma** model.

    A deliberate model-routing choice: the cheap open model does the throwaway
    HIGH/MEDIUM/LOW bucketing so the expensive Gemini 3.5 reasoning (the Analyst) is
    reserved for the items that matter. Fails soft — never wedges the run.

    Args:
        items: candidate signals/headlines to triage, one per line.

    Returns:
        A dict with `triage`: a list of {item, materiality} (HIGH/MEDIUM/LOW/UNKNOWN),
        and the `model` used.
    """
    lines = [ln.strip() for ln in items.splitlines() if ln.strip()]
    if not lines:
        return {"triage": [], "model": config.GEMMA_MODEL, "source": "gemma_triage"}
    numbered = "\n".join(f"{i + 1}. {ln}" for i, ln in enumerate(lines))
    prompt = (
        "You are a fast triage classifier. For each numbered item, judge its materiality to a "
        "crypto/markets watcher as HIGH, MEDIUM, or LOW. Reply with exactly one line per item in "
        "the form `N: LEVEL` and nothing else.\n\n" + numbered
    )
    try:
        resp = _genai().models.generate_content(
            model=config.GEMMA_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=1024),
        )
    except Exception as exc:  # noqa: BLE001 — triage is best-effort; the Analyst still runs
        return {"triage": [], "error": str(exc), "model": config.GEMMA_MODEL, "source": "gemma_triage"}

    levels = {}
    for line in (resp.text or "").splitlines():
        m = _LEVEL_RE.match(line)
        if m:
            levels[int(m.group(1))] = m.group(2).upper()
    triage = [{"item": ln, "materiality": levels.get(i + 1, "UNKNOWN")} for i, ln in enumerate(lines)]
    return {"triage": triage, "model": config.GEMMA_MODEL, "source": "gemma_triage"}
