"""Property-based tests for SpecialistPersona model and specialist registry.

Validates: Requirements 1.1, 1.2, 1.3, 2.4
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from business_coach.agents.specialists import (
    SPECIALIST_REGISTRY,
    SpecialistPersona,
    get_specialist,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Personality-mode keywords that must be rejected in system_prompt
_PERSONALITY_KEYWORDS = [
    "creative and imaginative",
    "balanced business advisor",
    "precise and factual",
]

# Safe printable text without control characters
_safe_char = st.characters(
    whitelist_categories=("L", "N", "P", "S", "Z"),
    blacklist_characters="\x00",
)

# Valid id: 1–100 chars, non-empty
_valid_id = st.text(alphabet=_safe_char, min_size=1, max_size=100).filter(lambda s: s.strip())

# Valid role_title: 1–200 chars, non-empty
_valid_role_title = st.text(alphabet=_safe_char, min_size=1, max_size=200).filter(lambda s: s.strip())

# Valid domain_description: 1–500 chars, non-empty
_valid_domain_description = st.text(alphabet=_safe_char, min_size=1, max_size=500).filter(lambda s: s.strip())

# Valid system_prompt: 1–2000 chars, non-empty, no personality keywords
_valid_system_prompt = st.text(alphabet=_safe_char, min_size=1, max_size=2000).filter(
    lambda s: s.strip() and not any(kw in s.lower() for kw in _PERSONALITY_KEYWORDS)
)

# Registry keys for filtering
_REGISTRY_KEYS = set(SPECIALIST_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Property 1: SpecialistPersona valid construction round-trip
# ---------------------------------------------------------------------------


class TestSpecialistPersonaValidConstruction:
    """Property 1: SpecialistPersona valid construction round-trip.

    For any valid combination of id (1–100 chars), role_title (1–200 chars),
    domain_description (1–500 chars), and system_prompt (1–2000 chars, not
    containing personality-mode keywords), constructing a SpecialistPersona
    SHALL succeed and all four fields SHALL be accessible with their original
    values.

    **Validates: Requirements 1.1**
    """

    @given(
        id=_valid_id,
        role_title=_valid_role_title,
        domain_description=_valid_domain_description,
        system_prompt=_valid_system_prompt,
    )
    @settings(max_examples=100)
    def test_valid_construction_round_trip(
        self,
        id: str,
        role_title: str,
        domain_description: str,
        system_prompt: str,
    ) -> None:
        """For any valid field values, construction succeeds and fields are accessible."""
        persona = SpecialistPersona(
            id=id,
            role_title=role_title,
            domain_description=domain_description,
            system_prompt=system_prompt,
        )
        assert persona.id == id
        assert persona.role_title == role_title
        assert persona.domain_description == domain_description
        assert persona.system_prompt == system_prompt


# ---------------------------------------------------------------------------
# Property 2: SpecialistPersona invalid input rejection
# ---------------------------------------------------------------------------


class TestSpecialistPersonaInvalidInputRejection:
    """Property 2: SpecialistPersona invalid input rejection.

    For any combination of fields where at least one required field is empty,
    or where system_prompt exceeds 2000 characters, or where system_prompt
    contains a personality-mode keyword phrase, constructing a SpecialistPersona
    SHALL raise a ValidationError.

    **Validates: Requirements 1.2, 1.3**
    """

    @given(
        role_title=_valid_role_title,
        domain_description=_valid_domain_description,
        system_prompt=_valid_system_prompt,
    )
    @settings(max_examples=100)
    def test_empty_id_raises_validation_error(
        self,
        role_title: str,
        domain_description: str,
        system_prompt: str,
    ) -> None:
        """An empty id field raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id="",
                role_title=role_title,
                domain_description=domain_description,
                system_prompt=system_prompt,
            )

    @given(
        id=_valid_id,
        domain_description=_valid_domain_description,
        system_prompt=_valid_system_prompt,
    )
    @settings(max_examples=100)
    def test_empty_role_title_raises_validation_error(
        self,
        id: str,
        domain_description: str,
        system_prompt: str,
    ) -> None:
        """An empty role_title field raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id=id,
                role_title="",
                domain_description=domain_description,
                system_prompt=system_prompt,
            )

    @given(
        id=_valid_id,
        role_title=_valid_role_title,
        system_prompt=_valid_system_prompt,
    )
    @settings(max_examples=100)
    def test_empty_domain_description_raises_validation_error(
        self,
        id: str,
        role_title: str,
        system_prompt: str,
    ) -> None:
        """An empty domain_description field raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id=id,
                role_title=role_title,
                domain_description="",
                system_prompt=system_prompt,
            )

    @given(
        id=_valid_id,
        role_title=_valid_role_title,
        domain_description=_valid_domain_description,
    )
    @settings(max_examples=100)
    def test_empty_system_prompt_raises_validation_error(
        self,
        id: str,
        role_title: str,
        domain_description: str,
    ) -> None:
        """An empty system_prompt field raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id=id,
                role_title=role_title,
                domain_description=domain_description,
                system_prompt="",
            )

    @given(
        id=_valid_id,
        role_title=_valid_role_title,
        domain_description=_valid_domain_description,
        oversized_prompt=st.text(alphabet=_safe_char, min_size=2001, max_size=3000).filter(
            lambda s: s.strip() and not any(kw in s.lower() for kw in _PERSONALITY_KEYWORDS)
        ),
    )
    @settings(max_examples=100)
    def test_oversized_system_prompt_raises_validation_error(
        self,
        id: str,
        role_title: str,
        domain_description: str,
        oversized_prompt: str,
    ) -> None:
        """A system_prompt exceeding 2000 characters raises ValidationError."""
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id=id,
                role_title=role_title,
                domain_description=domain_description,
                system_prompt=oversized_prompt,
            )

    @given(
        id=_valid_id,
        role_title=_valid_role_title,
        domain_description=_valid_domain_description,
        keyword_idx=st.integers(min_value=0, max_value=len(_PERSONALITY_KEYWORDS) - 1),
        prefix=st.text(alphabet=_safe_char, min_size=0, max_size=100),
        suffix=st.text(alphabet=_safe_char, min_size=0, max_size=100),
    )
    @settings(max_examples=100)
    def test_personality_keyword_in_system_prompt_raises_validation_error(
        self,
        id: str,
        role_title: str,
        domain_description: str,
        keyword_idx: int,
        prefix: str,
        suffix: str,
    ) -> None:
        """A system_prompt containing a personality-mode keyword raises ValidationError."""
        keyword = _PERSONALITY_KEYWORDS[keyword_idx]
        prompt_with_keyword = f"{prefix}{keyword}{suffix}"
        # Ensure the prompt is within max_length to isolate the keyword validation
        assume(len(prompt_with_keyword) <= 2000)
        assume(len(prompt_with_keyword) >= 1)
        with pytest.raises(ValidationError):
            SpecialistPersona(
                id=id,
                role_title=role_title,
                domain_description=domain_description,
                system_prompt=prompt_with_keyword,
            )


# ---------------------------------------------------------------------------
# Property 3: Unknown section name fallback
# ---------------------------------------------------------------------------


class TestUnknownSectionNameFallback:
    """Property 3: Unknown section name fallback.

    For any string that is not a key in SPECIALIST_REGISTRY, calling
    get_specialist() with that string SHALL return the fallback
    general-purpose business advisor SpecialistPersona (with id="general_advisor").

    **Validates: Requirements 2.4**
    """

    @given(
        section_name=st.text(min_size=0, max_size=200).filter(lambda s: s not in _REGISTRY_KEYS),
    )
    @settings(max_examples=100)
    def test_unknown_section_returns_general_advisor_fallback(
        self,
        section_name: str,
    ) -> None:
        """For any string not in the registry, get_specialist returns the fallback."""
        result = get_specialist(section_name)
        assert result.id == "general_advisor"
        assert result.role_title == "General Business Advisor"


# ---------------------------------------------------------------------------
# Property 5: Override save/read round-trip
# ---------------------------------------------------------------------------


class TestOverrideSaveReadRoundTrip:
    """Property 5: Override save/read round-trip.

    For any valid topic ID, section name, and specialist ID from the registry,
    saving an override and reading it back SHALL return the same specialist ID.

    **Validates: Requirements 7.2**
    """

    @given(
        topic_id=st.integers(min_value=1, max_value=10000),
        section_name=st.sampled_from(list(SPECIALIST_REGISTRY.keys())),
        specialist_id=st.sampled_from([p.id for p in SPECIALIST_REGISTRY.values()]),
    )
    @settings(max_examples=100)
    def test_save_and_read_returns_same_specialist_id(
        self,
        topic_id: int,
        section_name: str,
        specialist_id: str,
    ) -> None:
        """Saving an override and reading it back returns the same specialist ID."""
        import sqlite3

        from business_coach.db.repository import SpecialistOverrideRepository
        from business_coach.db.schema import init_schema

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        # Create the referenced topic so FK constraint is satisfied
        conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, f"topic_{topic_id}"))
        conn.commit()

        repo = SpecialistOverrideRepository(conn)
        repo.save(topic_id, section_name, specialist_id)

        result = repo.get_override(topic_id, section_name)
        assert result == specialist_id

        conn.close()


# ---------------------------------------------------------------------------
# Property 4: Prompt composition format and ordering
# ---------------------------------------------------------------------------


class TestPromptCompositionFormatAndOrdering:
    """Property 4: Prompt composition format and ordering.

    For any personality mode in {Creative, Balanced, Strict} and for any
    SpecialistPersona in the registry, the composed prompt SHALL start with
    the personality prompt text, followed by a ``\\n\\n`` delimiter, followed
    by the specialist's system_prompt. The personality text SHALL appear
    before the specialist text in the composed string.

    **Validates: Requirements 3.1, 3.2, 3.4, 10.2**
    """

    @given(
        personality_mode=st.sampled_from(["Creative", "Balanced", "Strict"]),
        section_name=st.sampled_from(list(SPECIALIST_REGISTRY.keys())),
    )
    @settings(max_examples=100, deadline=None)
    def test_composed_prompt_format_and_ordering(
        self,
        personality_mode: str,
        section_name: str,
    ) -> None:
        """Composed prompt starts with personality, has \\n\\n delimiter, ends with specialist prompt."""
        import sqlite3

        from business_coach.agents.workflow import PERSONALITY_PROMPTS, _compose_prompt
        from business_coach.db.repository import PersonalityPreferenceRepository
        from business_coach.db.schema import init_schema

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        # Create a topic
        topic_id = 1
        conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, "test_topic"))
        conn.commit()

        # Set the personality preference
        pref_repo = PersonalityPreferenceRepository(conn)
        pref_repo.save(topic_id, {"global": personality_mode})

        # Compose the prompt
        composed = _compose_prompt(topic_id, conn, section_name)

        personality_text = PERSONALITY_PROMPTS[personality_mode]
        specialist = SPECIALIST_REGISTRY[section_name]

        # Assert starts with personality text
        assert composed.startswith(personality_text)

        # Assert contains \n\n delimiter
        assert "\n\n" in composed

        # Assert ends with specialist system_prompt
        assert composed.endswith(specialist.system_prompt)

        # Assert personality appears before specialist
        personality_end = composed.index(personality_text) + len(personality_text)
        specialist_start = composed.index(specialist.system_prompt)
        assert personality_end <= specialist_start

        # Assert exact format: personality + \n\n + specialist.system_prompt
        expected = f"{personality_text}\n\n{specialist.system_prompt}"
        assert composed == expected

        conn.close()


# ---------------------------------------------------------------------------
# Property 6: Override precedence over registry default
# ---------------------------------------------------------------------------


class TestOverridePrecedenceOverRegistryDefault:
    """Property 6: Override precedence over registry default.

    For any section name in the registry and any valid override pointing to a
    different specialist in the registry, _resolve_specialist() SHALL return
    the overridden specialist instead of the registry default for that section.

    **Validates: Requirements 7.3**
    """

    @given(
        section_name=st.sampled_from(list(SPECIALIST_REGISTRY.keys())),
        data=st.data(),
    )
    @settings(max_examples=100, deadline=None)
    def test_override_takes_precedence_over_registry_default(
        self,
        section_name: str,
        data: st.DataObject,
    ) -> None:
        """An override pointing to a different specialist is returned instead of the default."""
        import sqlite3

        from business_coach.agents.workflow import _resolve_specialist
        from business_coach.db.repository import SpecialistOverrideRepository
        from business_coach.db.schema import init_schema

        # Get the default specialist for this section
        default_specialist = SPECIALIST_REGISTRY[section_name]

        # Pick a different specialist from the registry
        other_specialists = [p for p in SPECIALIST_REGISTRY.values() if p.id != default_specialist.id]
        assume(len(other_specialists) > 0)
        override_specialist = data.draw(st.sampled_from(other_specialists))

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        topic_id = 1
        conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, "test_topic"))
        conn.commit()

        # Save the override
        repo = SpecialistOverrideRepository(conn)
        repo.save(topic_id, section_name, override_specialist.id)

        # Resolve the specialist
        result = _resolve_specialist(section_name, topic_id, conn)

        # Assert the override is returned, not the default
        assert result.id == override_specialist.id
        assert result.id != default_specialist.id

        conn.close()


# ---------------------------------------------------------------------------
# Property 7: Override deletion reverts to registry default
# ---------------------------------------------------------------------------


class TestOverrideDeletionRevertsToRegistryDefault:
    """Property 7: Override deletion reverts to registry default.

    For any section name in the registry, saving an override and then deleting
    it SHALL cause _resolve_specialist() to return the same specialist as the
    registry default for that section.

    **Validates: Requirements 7.4**
    """

    @given(
        section_name=st.sampled_from(list(SPECIALIST_REGISTRY.keys())),
        override_specialist_id=st.sampled_from([p.id for p in SPECIALIST_REGISTRY.values()]),
    )
    @settings(max_examples=100, deadline=None)
    def test_deleting_override_reverts_to_registry_default(
        self,
        section_name: str,
        override_specialist_id: str,
    ) -> None:
        """After deleting an override, _resolve_specialist returns the registry default."""
        import sqlite3

        from business_coach.agents.workflow import _resolve_specialist
        from business_coach.db.repository import SpecialistOverrideRepository
        from business_coach.db.schema import init_schema

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        topic_id = 1
        conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, "test_topic"))
        conn.commit()

        repo = SpecialistOverrideRepository(conn)

        # Save an override
        repo.save(topic_id, section_name, override_specialist_id)

        # Delete the override
        repo.delete(topic_id, section_name)

        # Resolve the specialist — should be the registry default
        result = _resolve_specialist(section_name, topic_id, conn)
        expected_default = SPECIALIST_REGISTRY[section_name]

        assert result.id == expected_default.id

        conn.close()


# ---------------------------------------------------------------------------
# Property 8: Stale override fallback
# ---------------------------------------------------------------------------


class TestStaleOverrideFallback:
    """Property 8: Stale override fallback.

    For any specialist ID string that does not match any SpecialistPersona.id
    in the registry, if that string is saved as an override for a section,
    _resolve_specialist() SHALL return the registry default specialist for
    that section (not the stale override).

    **Validates: Requirements 8.3**
    """

    @given(
        section_name=st.sampled_from(list(SPECIALIST_REGISTRY.keys())),
        stale_id=st.text(alphabet=_safe_char, min_size=1, max_size=100).filter(
            lambda s: s.strip() and s not in {p.id for p in SPECIALIST_REGISTRY.values()}
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_stale_override_falls_back_to_registry_default(
        self,
        section_name: str,
        stale_id: str,
    ) -> None:
        """A stale override (non-existent specialist ID) falls back to registry default."""
        import sqlite3

        from business_coach.agents.workflow import _resolve_specialist
        from business_coach.db.repository import SpecialistOverrideRepository
        from business_coach.db.schema import init_schema

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        topic_id = 1
        conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, "test_topic"))
        conn.commit()

        repo = SpecialistOverrideRepository(conn)

        # Save an override with a non-existent specialist ID
        repo.save(topic_id, section_name, stale_id)

        # Resolve the specialist — should fall back to registry default
        result = _resolve_specialist(section_name, topic_id, conn)
        expected_default = SPECIALIST_REGISTRY[section_name]

        assert result.id == expected_default.id

        conn.close()
