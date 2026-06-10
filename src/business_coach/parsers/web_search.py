import logging

from ddgs import DDGS

from business_coach.db.models import WebSearchResult
from business_coach.exceptions import SearchServiceError

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 10) -> list[WebSearchResult]:
    """Perform a web search using DuckDuckGo and return WebSearchResult objects.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.

    Returns:
        A list of WebSearchResult objects.

    Raises:
        SearchServiceError: When DuckDuckGo is unavailable or the search fails.
    """
    results = []
    try:
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                WebSearchResult(
                    url=r.get("href", ""),
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    full_text=r.get("body", ""),  # We use snippet as full text fallback
                )
            )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise SearchServiceError("DuckDuckGo", e) from e
    return results
