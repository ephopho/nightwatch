"""Read-only tools for the Collector agent.

ADK turns a plain typed+documented function into a tool: the name, the type hints,
and this docstring become the schema the model sees — so keep the docstrings crisp.

These ship as STUBS that return sample data plus a `_stub` flag, so the whole
pipeline runs end-to-end today. Wire the real APIs in Week 1/2 (see the TODOs);
because the Analyst only reasons over whatever these return, the agent code above
them never changes when you swap stubs for live calls.
"""
from app.memory import store


def fetch_onchain(targets: str) -> dict:
    """Fetch NEW on-chain activity (transfers, contract calls) for the given targets.

    Args:
        targets: comma-separated wallet/contract addresses to check.

    Returns:
        A dict with an `events` list of new on-chain events since the last run.
    """
    # TODO: call a real explorer (e.g. blockchain.com / Etherscan-style) here, and
    #       use store.get_watermark/set_watermark(addr) to return only NEW events.
    events = [
        {"target": t.strip(), "type": "transfer", "detail": "STUB — wire a real explorer", "_stub": True}
        for t in targets.split(",")
        if t.strip()
    ]
    return {"events": events, "source": "onchain"}


def fetch_market(symbols: str) -> dict:
    """Fetch current prices and 24h change for the given market symbols.

    Args:
        symbols: comma-separated tickers, e.g. "BTC,ETH,SOL".

    Returns:
        A dict mapping each symbol to price + 24h change.
    """
    # TODO: call a real price API (e.g. CoinGecko /simple/price).
    quotes = {
        s.strip().upper(): {"usd": None, "change_24h": None, "_stub": True}
        for s in symbols.split(",")
        if s.strip()
    }
    return {"quotes": quotes, "source": "market"}


def web_search(query: str) -> dict:
    """Search the web for recent news/context relevant to the query (grounding).

    Args:
        query: what to look up, e.g. "Lido governance vote August 2026".

    Returns:
        A dict with a `results` list of {title, url, snippet}.
    """
    # TODO: wire a search/grounding provider (Vertex AI Grounding, or a search API).
    return {"results": [{"title": "STUB result", "url": "", "snippet": query, "_stub": True}]}
