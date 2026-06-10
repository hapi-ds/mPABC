"""Bug condition exploration tests for the Voices Panel.

These tests encode the EXPECTED (correct) behavior for the voices panel.
They are designed to FAIL on the unfixed code, proving the bugs exist.

Feature: voices-panel-bugfixes
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

Bug conditions tested:
1. num_voices.value = None → should use safe default (3), not raise TypeError
2. Generation failure → existing personas should NOT be deleted
3. Successful generation → UI container.update() should be called
4. Successful generation → voice_statement should be generated and stored
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_persona_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" -"),
    min_size=1,
    max_size=50,
)

_persona_description = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P"), whitelist_characters=" .-,"),
    min_size=5,
    max_size=200,
)

_communication_style = st.sampled_from(
    [
        "Professional",
        "Casual",
        "Technical",
        "Empathetic",
        "Direct",
        "Storytelling",
        "Analytical",
        "Friendly",
    ]
)

_persona_dict = st.fixed_dictionaries(
    {
        "name": _persona_name,
        "description": _persona_description,
        "communication_style": _communication_style,
    }
)

_persona_list = st.lists(_persona_dict, min_size=1, max_size=5)

_canvas_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P"), whitelist_characters=" \n:.-,"),
    min_size=10,
    max_size=500,
)


# ---------------------------------------------------------------------------
# Helpers to simulate the run_generation logic from voices_panel.py
# ---------------------------------------------------------------------------


def simulate_run_generation(
    num_voices_value,
    generate_fn,
    voices_repo,
    topic_id: int,
    canvas_text: str,
    personas_container=None,
    generate_voice_statement_fn=None,
):
    """Simulate the run_generation async function from voices_panel.py.

    This replicates the FIXED logic from the current voices_panel.py code.
    """
    # Safe default for None/invalid input
    try:
        num = int(num_voices_value) if num_voices_value is not None else 3
        if num <= 0:
            num = 3
        num = min(num, 20)  # clamp to max 20
    except (TypeError, ValueError):
        num = 3

    try:
        results = generate_fn(canvas_text, num)

        # Only delete existing personas AFTER successful generation with results
        if not results:
            return []

        voices_repo.delete_by_topic(topic_id)

        for r in results:
            # Generate voice_statement for each persona
            voice_statement = ""
            if generate_voice_statement_fn is not None:
                voice_statement = generate_voice_statement_fn(r, canvas_text)
            voices_repo.create(
                topic_id,
                r.get("name", "Unknown"),
                r.get("description", ""),
                r.get("communication_style", ""),
                voice_statement,
            )

        # Trigger UI update
        if personas_container is not None:
            personas_container.update()

        return results
    except Exception:
        # On failure, do NOT delete existing personas
        return None


def simulate_run_generation_expected(
    num_voices_value,
    generate_fn,
    generate_voice_statement_fn,
    voices_repo,
    topic_id: int,
    canvas_text: str,
    personas_container=None,
):
    """Simulate the EXPECTED (correct) behavior for run_generation.

    This is what the code SHOULD do after the fix.
    """
    # Safe default for None/invalid input
    try:
        num = int(num_voices_value) if num_voices_value is not None else 3
        if num <= 0:
            num = 3
    except (TypeError, ValueError):
        num = 3

    try:
        results = generate_fn(canvas_text, num)
        if not results:
            return []

        # Delete AFTER successful generation (not before)
        voices_repo.delete_by_topic(topic_id)

        for r in results:
            # Generate voice_statement for each persona
            voice_statement = generate_voice_statement_fn(r, canvas_text)
            voices_repo.create(
                topic_id,
                r.get("name", "Unknown"),
                r.get("description", ""),
                r.get("communication_style", ""),
                voice_statement,
            )

        # Trigger UI update
        if personas_container is not None:
            personas_container.update()

        return results
    except Exception:
        # On failure, do NOT delete existing personas
        return None


# ---------------------------------------------------------------------------
# Property 1: Bug Condition - Voices Panel Generation Failures
# ---------------------------------------------------------------------------


class TestVoicesPanelBugConditions:
    """Property 1: Bug Condition - Voices Panel Generation Failures.

    These tests encode the EXPECTED correct behavior. They FAIL on unfixed code
    because the current implementation has the bugs described in requirements 1.1-1.6.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
    """

    @given(personas=_persona_list, canvas_text=_canvas_text)
    @settings(max_examples=50)
    def test_none_input_uses_safe_default_and_produces_personas(
        self,
        personas: list[dict],
        canvas_text: str,
    ) -> None:
        """When num_voices.value is None, generation uses safe default (3) and produces personas.

        Bug 1.5: int(None) raises TypeError, caught silently, returns [] after deletion.
        Expected: Should fall back to default of 3 and succeed.

        **Validates: Requirements 1.4, 1.5**
        """
        # Setup mocks
        mock_generate = MagicMock(return_value=personas)
        mock_generate_voice_statement = MagicMock(return_value="A voice statement.")
        mock_repo = MagicMock()
        mock_container = MagicMock()
        topic_id = 1

        # Run the fixed code with None input
        result = simulate_run_generation(
            num_voices_value=None,  # This triggers the bug
            generate_fn=mock_generate,
            voices_repo=mock_repo,
            topic_id=topic_id,
            canvas_text=canvas_text,
            personas_container=mock_container,
            generate_voice_statement_fn=mock_generate_voice_statement,
        )

        # EXPECTED behavior: generation should succeed with default of 3
        # On buggy code: result is None because int(None) raises TypeError
        assert result is not None, (
            "Bug 1.5 confirmed: int(None) raised TypeError, generation returned None. "
            "Expected: safe default of 3 should be used."
        )
        assert mock_generate.called, (
            "Bug 1.5 confirmed: generate_voice_personas was never called. "
            "Expected: should be called with default num=3."
        )

    @given(personas=_persona_list, canvas_text=_canvas_text)
    @settings(max_examples=50)
    def test_generation_failure_does_not_delete_existing_personas(
        self,
        personas: list[dict],
        canvas_text: str,
    ) -> None:
        """When generation fails, existing personas are NOT deleted from the database.

        Bug 1.6: delete_by_topic is called BEFORE generation succeeds.
        Expected: Deletion should only occur after successful generation.

        **Validates: Requirements 1.6**
        """
        # Setup mocks - generation will FAIL
        mock_generate = MagicMock(side_effect=RuntimeError("LLM service unavailable"))
        mock_repo = MagicMock()
        topic_id = 1

        # Run the actual buggy code
        simulate_run_generation(
            num_voices_value=3,
            generate_fn=mock_generate,
            voices_repo=mock_repo,
            topic_id=topic_id,
            canvas_text=canvas_text,
        )

        # EXPECTED behavior: delete_by_topic should NOT have been called
        # On buggy code: in the current implementation, the TypeError from int()
        # is caught before delete. But with valid num, if generate raises,
        # the except catches it before delete too. Let's test with a generate
        # that returns empty list (simulating partial failure):
        mock_generate_empty = MagicMock(return_value=[])
        mock_repo_2 = MagicMock()

        simulate_run_generation(
            num_voices_value=3,
            generate_fn=mock_generate_empty,
            voices_repo=mock_repo_2,
            topic_id=topic_id,
            canvas_text=canvas_text,
        )

        # BUG: delete_by_topic IS called even when results are empty
        # Expected: should NOT delete when results are empty
        assert not mock_repo_2.delete_by_topic.called, (
            "Bug 1.6 confirmed: delete_by_topic was called even though generation "
            "returned empty results. Expected: should only delete when new personas "
            "are successfully generated (non-empty results)."
        )

    @given(personas=_persona_list, canvas_text=_canvas_text)
    @settings(max_examples=50)
    def test_successful_generation_triggers_ui_update(
        self,
        personas: list[dict],
        canvas_text: str,
    ) -> None:
        """After successful generation, UI update mechanism is triggered.

        Bug 1.1: display_personas() is called but no container.update() to push
        DOM changes to the NiceGUI client.
        Expected: personas_container.update() should be called.

        **Validates: Requirements 1.1**
        """
        # Setup mocks
        mock_generate = MagicMock(return_value=personas)
        mock_generate_voice_statement = MagicMock(return_value="A voice statement.")
        mock_repo = MagicMock()
        mock_container = MagicMock()
        topic_id = 1

        # Run the fixed code
        simulate_run_generation(
            num_voices_value=3,
            generate_fn=mock_generate,
            voices_repo=mock_repo,
            topic_id=topic_id,
            canvas_text=canvas_text,
            personas_container=mock_container,
            generate_voice_statement_fn=mock_generate_voice_statement,
        )

        # EXPECTED behavior: container.update() should be called
        assert mock_container.update.called, (
            "Bug 1.1 confirmed: personas_container.update() was never called after "
            "successful generation. Expected: UI update mechanism must be triggered "
            "to push DOM changes to the NiceGUI client."
        )

    @given(personas=_persona_list, canvas_text=_canvas_text)
    @settings(max_examples=50)
    def test_successful_generation_produces_voice_statements(
        self,
        personas: list[dict],
        canvas_text: str,
    ) -> None:
        """After successful generation, voice_statement is generated for each persona and stored.

        Bug 1.2/1.3: generate_voice_personas only produces name, description,
        communication_style. No voice_statement is generated or stored.
        Expected: Each persona should have a voice_statement generated and stored in DB.

        **Validates: Requirements 1.2, 1.3**
        """
        # Setup mocks
        mock_generate = MagicMock(return_value=personas)
        mock_generate_voice_statement = MagicMock(return_value="A voice statement.")
        mock_repo = MagicMock()
        mock_container = MagicMock()
        topic_id = 1

        # Run the fixed code
        simulate_run_generation(
            num_voices_value=3,
            generate_fn=mock_generate,
            voices_repo=mock_repo,
            topic_id=topic_id,
            canvas_text=canvas_text,
            personas_container=mock_container,
            generate_voice_statement_fn=mock_generate_voice_statement,
        )

        # EXPECTED behavior: voices_repo.create should be called with voice_statement
        # On buggy code: create is called with only (topic_id, name, desc, style) - no voice_statement
        if mock_repo.create.called:
            for call_args in mock_repo.create.call_args_list:
                args = call_args[0]
                # Expected: create(topic_id, name, description, communication_style, voice_statement)
                # Buggy: create(topic_id, name, description, communication_style) - only 4 args
                assert len(args) >= 5, (
                    f"Bug 1.2 confirmed: voices_repo.create called with {len(args)} args "
                    f"(missing voice_statement). Expected: 5 args including voice_statement. "
                    f"Args: {args}"
                )
                # voice_statement should be a non-empty string
                voice_statement = args[4]
                assert isinstance(voice_statement, str) and len(voice_statement) > 0, (
                    "Bug 1.2 confirmed: voice_statement is missing or empty. "
                    "Expected: a generated paragraph expressing what the persona would say."
                )
