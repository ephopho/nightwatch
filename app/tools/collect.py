"""Read-only tools for the Collector agent.

ADK turns a plain typed+documented function into a tool: the name, type hints, and
docstring become the schema the model sees — so keep the docstrings crisp.

`fetch_market` and `fetch_onchain` are now LIVE (CoinGecko + blockchain.com's explorer
gateway, the same sources ChainAlert used). `web_search` is still a stub — wire a
grounding/search provider when you want news context. On-chain uses Firestore watermarks
so each run only surfaces genuinely NEW transactions (seeds silently on first sighting).
"""
import re

import requests

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


def web_search(query: str) -> dict:
    """Search the web for recent news/context relevant to the query (grounding).

    Args:
        query: what to look up, e.g. "Lido governance vote August 2026".

    Returns:
        A dict with a `results` list of {title, url, snippet}.
    """
    # TODO: wire a search/grounding provider (Vertex AI Grounding, or a search API).
    return {"results": [{"title": "STUB result", "url": "", "snippet": query, "_stub": True}]}
