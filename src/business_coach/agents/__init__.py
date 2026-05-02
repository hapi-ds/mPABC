"""Agents package for the Business Coach system."""

from business_coach.exceptions import (
    AgentError,
    LLMConnectionError,
    SourceUnavailableError,
)

__all__ = [
    "AgentError",
    "LLMConnectionError",
    "SourceUnavailableError",
]
