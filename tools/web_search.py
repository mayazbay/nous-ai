"""Web search for Researcher agent — Karpathy-style deep research."""

import os
from tools.search_tracker import log_search, get_monthly_usage


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using Tavily API. Tracks usage against monthly limit."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return [{"title": "No search API key", "content": "TAVILY_API_KEY not set. Using RAG only."}]

    # Check usage before searching
    usage = get_monthly_usage()
    if usage.get("remaining", 1000) <= 0:
        return [{"title": "Search limit reached", "content": f"Monthly limit of {usage['limit']} searches reached. Using RAG only."}]

    if usage.get("alert"):
        print(f"[Search] WARNING: {usage['total']}/{usage['limit']} searches used this month")

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=max_results)
        parsed = [
            {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:500]}
            for r in results.get("results", [])
        ]

        # Log the search
        log_search(query, len(parsed))

        return parsed
    except Exception as e:
        log_search(query, 0)  # Log failed searches too
        return [{"title": "Search failed", "content": str(e)}]
