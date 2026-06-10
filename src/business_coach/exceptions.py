"""Custom exception hierarchy for the Business Coach system."""


class AgentError(Exception):
    """Base exception for agent errors."""

    pass


class LLMConnectionError(AgentError):
    """Raised when LM Studio is unreachable."""

    pass


class SourceUnavailableError(AgentError):
    """Raised when an external data source is unreachable.

    Attributes:
        source_name: Name of the unavailable data source.
        original_error: The underlying exception that caused the failure.
    """

    def __init__(self, source_name: str, original_error: Exception) -> None:
        self.source_name = source_name
        self.original_error = original_error
        super().__init__(f"Source {source_name} unavailable: {original_error}")


class SearchServiceError(SourceUnavailableError):
    """Raised when the DuckDuckGo search service fails.

    Attributes:
        source_name: Name of the search service (defaults to "DuckDuckGo").
        original_error: The underlying exception that caused the failure.
    """

    def __init__(self, source_name: str = "DuckDuckGo", original_error: Exception | None = None) -> None:
        if original_error is None:
            original_error = Exception("Unknown search service error")
        super().__init__(source_name, original_error)
