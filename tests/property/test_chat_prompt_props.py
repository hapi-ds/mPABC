"""Property-based tests for chat prompt construction.

Feature: placeholder-to-real-implementation, Property 7: Chat prompt contains context and question

Validates: Requirements 5.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.gui.chat_panel import build_chat_prompt

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# An invention context dict with a non-empty "primary_description" field
_invention_context = st.fixed_dictionaries({"primary_description": st.text(min_size=1)})

# Non-empty user question
_question = st.text(min_size=1)


# ---------------------------------------------------------------------------
# Property 7: Chat prompt contains context and question
# Feature: placeholder-to-real-implementation, Property 7: Chat prompt contains context and question
# ---------------------------------------------------------------------------


class TestChatPromptContainsContextAndQuestion:
    """Property 7: Chat prompt contains context and question.

    For any invention context dict (with a "primary_description" field) and
    any non-empty user question string, the prompt constructed by the chat
    panel shall contain the user question text and shall contain the
    primary_description from the context when provided.

    **Validates: Requirements 5.2**
    """

    @given(context=_invention_context, question=_question)
    @settings(max_examples=100)
    def test_prompt_contains_question(
        self,
        context: dict,
        question: str,
    ) -> None:
        """The constructed prompt always contains the user question."""
        prompt = build_chat_prompt(question, invention_context=context)
        assert question in prompt

    @given(
        context=_invention_context,
        question=_question,
    )
    @settings(max_examples=100)
    def test_prompt_contains_all_context_texts(
        self,
        context: dict,
        question: str,
    ) -> None:
        """The constructed prompt contains the primary_description from context."""
        prompt = build_chat_prompt(question, invention_context=context)
        assert context["primary_description"] in prompt

    @given(question=_question)
    @settings(max_examples=100)
    def test_empty_context_still_contains_question(
        self,
        question: str,
    ) -> None:
        """When no context is provided, the prompt still contains the question."""
        prompt = build_chat_prompt(question)
        assert question in prompt
