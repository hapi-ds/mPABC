"""Pydantic data models for the business coach database records.

Defines domain models used across the application for data validation,
serialization, and transfer between layers. Models correspond to the
SQLite tables defined in schema.py, plus structured output types for
agent results.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class Topic(BaseModel):
    """A user-created workspace grouping research, chat, and drafts."""

    id: int | None = None
    name: str
    created_at: datetime = Field(default_factory=_utc_now)


class ResearchSession(BaseModel):
    """A record of an internet search query and its results."""

    id: int | None = None
    topic_id: int
    query: str
    search_date: datetime = Field(default_factory=_utc_now)
    status: str = "pending"


class WebSearchResult(BaseModel):
    """A document retrieved from web search."""

    id: int | None = None
    session_id: int | None = None
    url: str
    title: str
    snippet: str
    full_text: str | None = None
    source: str = "web"
    discovered_date: datetime = Field(default_factory=_utc_now)
    embedding: bytes | None = None


class ChatMessage(BaseModel):
    """A single message in the AI chat history."""

    id: int | None = None
    topic_id: int
    role: str  # "user" or "assistant"
    message: str
    timestamp: datetime = Field(default_factory=_utc_now)


class BusinessIdea(BaseModel):
    """Structured output from the initial idea interview."""

    problem_statement: str
    solution_description: str
    target_audience: str
    unique_value_proposition: str


class BusinessIdeaRecord(BaseModel):
    """Persisted business idea for a topic."""

    id: int | None = None
    topic_id: int
    primary_description: str
    search_terms: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)


class SourcePreference(BaseModel):
    """Per-topic source selection preference."""

    id: int | None = None
    topic_id: int
    source_name: str
    enabled: bool = True


class CanvasElement(BaseModel):
    """A single element in the Business Model Canvas."""

    id: int | None = None
    topic_id: int
    element_name: str  # e.g. "Key Partners", "Value Propositions", etc.
    content: str
    user_feedback: str | None = None
    last_updated: datetime = Field(default_factory=_utc_now)


class VoicePersona(BaseModel):
    """An AI generated persona/voice based on the target audience."""

    id: int | None = None
    topic_id: int
    name: str
    description: str
    communication_style: str
    last_updated: datetime = Field(default_factory=_utc_now)


class PlanSection(BaseModel):
    """A section of the business plan."""

    id: int | None = None
    topic_id: int
    section_name: str  # e.g. "Executive Summary", "Market Analysis"
    content: str
    user_feedback: str | None = None
    last_updated: datetime = Field(default_factory=_utc_now)
