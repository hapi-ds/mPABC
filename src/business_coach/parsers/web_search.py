from ddgs import DDGS
from business_coach.db.models import WebSearchResult

def search_web(query: str, max_results: int = 10) -> list[WebSearchResult]:
    """Perform a web search using DuckDuckGo and return WebSearchResult objects."""
    results = []
    try:
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=max_results):
            results.append(WebSearchResult(
                url=r.get("href", ""),
                title=r.get("title", ""),
                snippet=r.get("body", ""),
                full_text=r.get("body", "")  # We use snippet as full text fallback
            ))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Search failed: {e}")
    return results
