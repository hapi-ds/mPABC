"""Unit tests for personality mode mapping and defaults.

Validates: Requirements 13.1, 13.2, 13.3, 13.5
"""

import sqlite3

import pytest

from business_coach.agents.workflow import PERSONALITY_PROMPTS, _get_personality_prompt
from business_coach.db.repository import PersonalityPreferenceRepository
from business_coach.db.schema import init_schema


@pytest.fixture
def in_memory_db():
    """Provide a fresh in-memory SQLite connection with full schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    # Create a topic for testing
    conn.execute("INSERT INTO topics (id, name) VALUES (1, 'Test Topic')")
    conn.commit()
    yield conn
    conn.close()


class TestPersonalityPrompts:
    """Test PERSONALITY_PROMPTS dict contains entries for all modes."""

    def test_contains_creative_entry(self) -> None:
        """Validates: Requirement 13.1"""
        assert "Creative" in PERSONALITY_PROMPTS
        assert len(PERSONALITY_PROMPTS["Creative"]) > 0

    def test_contains_balanced_entry(self) -> None:
        """Validates: Requirement 13.2"""
        assert "Balanced" in PERSONALITY_PROMPTS
        assert len(PERSONALITY_PROMPTS["Balanced"]) > 0

    def test_contains_strict_entry(self) -> None:
        """Validates: Requirement 13.3"""
        assert "Strict" in PERSONALITY_PROMPTS
        assert len(PERSONALITY_PROMPTS["Strict"]) > 0

    def test_creative_prompt_mentions_creative(self) -> None:
        """Creative prompt should instruct creative behavior."""
        assert "creative" in PERSONALITY_PROMPTS["Creative"].lower()

    def test_balanced_prompt_mentions_balanced(self) -> None:
        """Balanced prompt should instruct balanced behavior."""
        assert "balanced" in PERSONALITY_PROMPTS["Balanced"].lower()

    def test_strict_prompt_mentions_precise(self) -> None:
        """Strict prompt should instruct precise/factual behavior."""
        assert "precise" in PERSONALITY_PROMPTS["Strict"].lower()


class TestGetPersonalityPromptDefault:
    """Test _get_personality_prompt returns Balanced when no preference saved."""

    def test_returns_balanced_when_no_preference_saved(self, in_memory_db: sqlite3.Connection) -> None:
        """Validates: Requirement 13.5"""
        result = _get_personality_prompt(topic_id=1, conn=in_memory_db)
        assert result == PERSONALITY_PROMPTS["Balanced"]


class TestGetPersonalityPromptSavedModes:
    """Test _get_personality_prompt returns correct prompt for each saved mode."""

    def test_returns_creative_prompt_when_creative_saved(self, in_memory_db: sqlite3.Connection) -> None:
        """Validates: Requirement 13.1"""
        repo = PersonalityPreferenceRepository(in_memory_db)
        repo.save(topic_id=1, preferences={"global": "Creative"})

        result = _get_personality_prompt(topic_id=1, conn=in_memory_db)
        assert result == PERSONALITY_PROMPTS["Creative"]

    def test_returns_balanced_prompt_when_balanced_saved(self, in_memory_db: sqlite3.Connection) -> None:
        """Validates: Requirement 13.2"""
        repo = PersonalityPreferenceRepository(in_memory_db)
        repo.save(topic_id=1, preferences={"global": "Balanced"})

        result = _get_personality_prompt(topic_id=1, conn=in_memory_db)
        assert result == PERSONALITY_PROMPTS["Balanced"]

    def test_returns_strict_prompt_when_strict_saved(self, in_memory_db: sqlite3.Connection) -> None:
        """Validates: Requirement 13.3"""
        repo = PersonalityPreferenceRepository(in_memory_db)
        repo.save(topic_id=1, preferences={"global": "Strict"})

        result = _get_personality_prompt(topic_id=1, conn=in_memory_db)
        assert result == PERSONALITY_PROMPTS["Strict"]


class TestGetPersonalityPromptDBFailure:
    """Test DB read failure falls back to Balanced default."""

    def test_falls_back_to_balanced_on_db_error(self) -> None:
        """Validates: Requirement 13.5 — DB failure fallback."""
        # Use a closed connection to simulate a DB error
        conn = sqlite3.connect(":memory:")
        conn.close()

        result = _get_personality_prompt(topic_id=1, conn=conn)
        assert result == PERSONALITY_PROMPTS["Balanced"]
