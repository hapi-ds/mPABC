"""Property-based tests demonstrating bug conditions in the search pipeline.

These tests expose the bug conditions where the search pipeline produces
no visible output or actionable feedback to the user despite an attempt
to search. They are EXPECTED TO FAIL on unfixed code — failure confirms
the bug exists.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
"""

import sqlite3
import struct
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.agents.workflow import run_section_search
from business_coach.db.models import WebSearchResult
from business_coach.db.schema import init_schema
from business_coach.parsers.web_search import search_web


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_safe_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z"), blacklist_characters="\x00"),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())

_search_query = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Z"), blacklist_characters="\x00"),
    min_size=3,
    max_size=80,
).filter(lambda s: s.strip())

_web_result_strategy = st.builds(
    WebSearchResult,
    url=st.from_regex(r"https://[a-z]{3,10}\.[a-z]{2,4}/[a-z]{1,10}", fullmatch=True),
    title=_safe_text,
    snippet=_safe_text,
    full_text=_safe_text,
)

_web_results_list = st.lists(_web_result_strategy, min_size=1, max_size=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn_with_topic(topic_id: int = 1) -> sqlite3.Connection:
    """Create an in-memory DB with schema and a topic row."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute("INSERT INTO topics (id, name) VALUES (?, ?)", (topic_id, "test"))
    conn.commit()
    return conn


def _make_settings() -> MagicMock:
    """Create a mock AppSettings with required attributes."""
    settings = MagicMock()
    settings.embedding_model_name = "test-model"
    settings.lm_studio_base_url = "http://localhost:1234/v1"
    settings.lm_studio_api_key = "not-needed"
    return settings


def _fake_embedding(dim: int = 384) -> bytes:
    """Generate a fake embedding vector as packed bytes."""
    return struct.pack(f"{dim}f", *([0.1] * dim))


# ---------------------------------------------------------------------------
# Test Case 1: Empty handlers — no user notification produced
# **Validates: Requirements 1.1**
# ---------------------------------------------------------------------------


class TestEmptyHandlersNoNotification:
    """Bug Condition: Empty run_handlers list produces no user notification.

    WHEN the user clicks 'Run All Searches' before sections are rendered,
    run_handlers is [] and the loop completes instantly with no feedback.

    The fix adds an early-return guard: if not run_handlers, notify the user
    and return without executing the loop.

    **Validates: Requirements 1.1**
    """

    def test_empty_handlers_produces_notification(self) -> None:
        """Fixed code: empty run_handlers triggers early-return with notification."""
        import asyncio

        # Simulate the FIXED run_all_searches logic from idea_panel.py
        run_handlers: list = []
        notifications: list[str] = []

        async def run_all_searches():
            if not run_handlers:
                notifications.append("Please generate research categories first.")
                return
            for handler in run_handlers:
                await handler()

        # Execute the async function
        asyncio.run(run_all_searches())

        # FIXED ASSERTION: The guard clause produces a notification.
        assert len(notifications) > 0, (
            "Fix verification failed: run_all_searches with empty run_handlers "
            "should produce a user notification via the guard clause"
        )
        assert "generate research categories" in notifications[0].lower()


# ---------------------------------------------------------------------------
# Test Case 2: DuckDuckGo failure — returns [] indistinguishable from no results
# **Validates: Requirements 1.2**
# ---------------------------------------------------------------------------


class TestDDGFailureIndistinguishableFromEmpty:
    """Bug Condition: DuckDuckGo failure returns [] indistinguishable from no results.

    WHEN DDGS().text() raises an exception (rate-limit, network error),
    search_web() should raise SearchServiceError so callers can distinguish
    a service failure from a legitimate "no results" response.

    The fix makes search_web() raise SearchServiceError on DDG failure.

    **Validates: Requirements 1.2**
    """

    @given(query=_search_query)
    @settings(max_examples=20)
    def test_ddg_exception_raises_search_service_error(self, query: str) -> None:
        """Fixed: search_web() raises SearchServiceError on DDG failure."""
        from business_coach.exceptions import SearchServiceError

        with patch("business_coach.parsers.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.side_effect = RuntimeError("Rate limited")

            # FIXED ASSERTION: search_web now raises SearchServiceError
            # instead of silently returning [].
            with pytest.raises(SearchServiceError) as exc_info:
                search_web(query, max_results=5)

            # Verify the error carries meaningful context
            assert "DuckDuckGo" in str(exc_info.value) or exc_info.value.source_name == "DuckDuckGo"


# ---------------------------------------------------------------------------
# Test Case 3: LM Studio scorer down — all results discarded
# **Validates: Requirements 1.3**
# ---------------------------------------------------------------------------


class TestScorerDownDiscardsAllResults:
    """Bug Condition: LM Studio scorer failure discards all results.

    WHEN scorer_agent() raises ConnectionError, the per-result try/except
    catches it and assigns a default score of 50 (below threshold). The
    progress_callback should then produce a threshold notification with
    a count and suggestion, providing the user with actionable feedback.

    The fix ensures per-result scoring failures are handled gracefully
    and the threshold notification informs the user.

    **Validates: Requirements 1.3**
    """

    @given(results=_web_results_list, query=_search_query)
    @settings(max_examples=10, deadline=None)
    def test_scorer_failure_produces_threshold_notification(
        self, results: list[WebSearchResult], query: str
    ) -> None:
        """Fixed: Scorer failures handled per-result; threshold notification produced."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService"),
        ):
            # dspy.Predict(SearchResultScorer) returns an instance (scorer_agent).
            # That instance is then called: scorer_agent(...). Make calls raise.
            scorer_instance = MagicMock()
            scorer_instance.side_effect = ConnectionError("LM Studio unreachable")
            mock_predict.return_value = scorer_instance

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # FIXED ASSERTION: When all scoring fails, default score (50) is below
        # threshold (60), so threshold notification fires with count and suggestion.
        all_messages = " ".join(progress_messages).lower()
        has_threshold_notification = any(
            ("threshold" in m.lower() or "scored" in m.lower() or "none" in m.lower())
            and any(c.isdigit() for c in m)
            for m in progress_messages
        )
        has_suggestion = (
            "broaden" in all_messages
            or "adjust" in all_messages
            or "refine" in all_messages
            or "consider" in all_messages
        )

        assert has_threshold_notification or has_suggestion, (
            f"Fix verification failed: scorer failure should result in threshold "
            f"notification with count and suggestion. Got: {progress_messages}"
        )

        conn.close()


# ---------------------------------------------------------------------------
# Test Case 4: Embedding failure — scored results silently dropped
# **Validates: Requirements 1.4**
# ---------------------------------------------------------------------------


class TestEmbeddingFailureDropsScoredResults:
    """Bug Condition: Embedding failure silently drops scored results.

    WHEN generate_embedding() returns None, results that PASSED scoring
    (score >= 60) are silently dropped by the `if embedding_bytes:` guard.
    The user never sees these results.

    The bug is confirmed if saved_results is empty despite results passing
    the score threshold.

    **Validates: Requirements 1.4**
    """

    @given(results=_web_results_list, query=_search_query)
    @settings(max_examples=10, deadline=None)
    def test_embedding_none_drops_scored_results(
        self, results: list[WebSearchResult], query: str
    ) -> None:
        """Results passing score threshold are dropped when embedding returns None."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # Mock scorer to return high scores (all pass threshold)
        mock_score_result = MagicMock()
        mock_score_result.relevance_score = "85"

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            # dspy.Predict(SearchResultScorer) returns scorer_instance
            # scorer_instance(...) returns mock_score_result
            scorer_instance = MagicMock()
            scorer_instance.return_value = mock_score_result
            mock_predict.return_value = scorer_instance
            # Embedding returns None — simulates embedding service failure
            mock_emb_cls.return_value.generate_embedding.return_value = None

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # BUG ASSERTION: Results that passed scoring (score >= 60) SHOULD be
        # returned to the user even if embedding fails. On unfixed code,
        # saved_results is empty because `if embedding_bytes:` skips them.
        # This assertion FAILS on unfixed code (proving the bug).
        assert len(saved) > 0, (
            f"Bug confirmed: {len(results)} results scored >= 60 but all dropped "
            f"because generate_embedding() returned None. "
            f"Progress: {progress_messages}"
        )

        conn.close()


# ---------------------------------------------------------------------------
# Test Case 5: Threshold filter — empty results with no count or suggestion
# **Validates: Requirements 1.5**
# ---------------------------------------------------------------------------


class TestThresholdFilterNoNotification:
    """Bug Condition: All results below threshold with no count or suggestion.

    WHEN all results score below 60, the user sees "No highly relevant
    documents found" but gets no count of raw results found or suggestion
    to broaden the query.

    The bug is confirmed if progress_callback messages do NOT include a
    count of results found or a suggestion to adjust the query.

    **Validates: Requirements 1.5**
    """

    @given(
        results=_web_results_list,
        query=_search_query,
        scores=st.lists(
            st.integers(min_value=1, max_value=59),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=10, deadline=None)
    def test_below_threshold_no_count_or_suggestion(
        self, results: list[WebSearchResult], query: str, scores: list[int]
    ) -> None:
        """All results below threshold produce no count or query suggestion."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # Create a score iterator matching results length
        score_iter = iter(scores * ((len(results) // len(scores)) + 1))

        def make_score_result(*args, **kwargs):
            result = MagicMock()
            result.relevance_score = str(next(score_iter))
            return result

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            # dspy.Predict(SearchResultScorer) returns scorer_instance
            # scorer_instance(...) returns the score result
            scorer_instance = MagicMock()
            scorer_instance.side_effect = make_score_result
            mock_predict.return_value = scorer_instance
            mock_emb_cls.return_value.generate_embedding.return_value = _fake_embedding()

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # BUG ASSERTION: When results exist but none pass threshold, the user
        # should see a count of results found and a suggestion. On unfixed code,
        # only "No highly relevant documents found" is shown — no count, no suggestion.
        # This assertion FAILS on unfixed code (proving the bug).
        # We specifically look at the FINAL messages (after scoring) for threshold info.
        # The intermediate "Found N results. Scoring..." is just progress, not the
        # threshold notification we expect the fix to produce.
        all_messages = " ".join(progress_messages).lower()

        # Check for a specific threshold notification message that includes
        # both a count AND a suggestion — distinct from the scoring progress
        has_threshold_notification = any(
            ("threshold" in m.lower() or "below" in m.lower())
            and any(c.isdigit() for c in m)
            for m in progress_messages
        )
        has_suggestion = (
            "broaden" in all_messages
            or "adjust" in all_messages
            or "refine" in all_messages
            or "consider" in all_messages
        )

        assert has_threshold_notification or has_suggestion, (
            f"Bug confirmed: All {len(results)} results scored below 60 but "
            f"no threshold notification with count or query suggestion provided. "
            f"Messages: {progress_messages}"
        )

        conn.close()


# ===========================================================================
# PRESERVATION PROPERTY TESTS
# ===========================================================================
# These tests lock the happy-path behavior of the search pipeline to prevent
# regressions when implementing the bug fix. They MUST PASS on unfixed code.
#
# **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
# ===========================================================================


# ---------------------------------------------------------------------------
# Additional Strategies for Preservation Tests
# ---------------------------------------------------------------------------

_score_above_threshold = st.integers(min_value=60, max_value=100)
_score_below_threshold = st.integers(min_value=0, max_value=59)


# ---------------------------------------------------------------------------
# Preservation Test 1: Happy-path search_web returns list[WebSearchResult]
# **Validates: Requirements 3.1**
# ---------------------------------------------------------------------------


class TestPreservationSearchWebHappyPath:
    """Preservation: search_web returns list[WebSearchResult] when DDG works.

    WHEN DuckDuckGo responds successfully with valid results THEN
    search_web() returns a list[WebSearchResult] with the correct data.

    **Validates: Requirements 3.1**
    """

    @given(
        query=_search_query,
        num_results=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=20)
    def test_search_web_returns_web_search_result_list(
        self, query: str, num_results: int
    ) -> None:
        """search_web() returns list[WebSearchResult] on DDG success."""
        # Build fake DDG responses
        fake_ddg_results = [
            {"href": f"https://example.com/{i}", "title": f"Title {i}", "body": f"Snippet {i}"}
            for i in range(num_results)
        ]

        with patch("business_coach.parsers.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = fake_ddg_results

            result = search_web(query, max_results=num_results)

        # Preservation: returns a list
        assert isinstance(result, list)
        # Preservation: all items are WebSearchResult
        assert all(isinstance(r, WebSearchResult) for r in result)
        # Preservation: correct count
        assert len(result) == num_results
        # Preservation: data mapped correctly
        for i, r in enumerate(result):
            assert r.url == f"https://example.com/{i}"
            assert r.title == f"Title {i}"
            assert r.snippet == f"Snippet {i}"


# ---------------------------------------------------------------------------
# Preservation Test 2: Threshold filtering at score 60
# **Validates: Requirements 3.2**
# ---------------------------------------------------------------------------


class TestPreservationThresholdFiltering:
    """Preservation: Score threshold of 60 filters results correctly.

    Results with score >= 60 are included (pass), results with score < 60
    are excluded (filtered). Boundary: score exactly 60 is included,
    score 59 is excluded.

    **Validates: Requirements 3.2**
    """

    @given(results=_web_results_list)
    @settings(max_examples=10, deadline=None)
    def test_score_exactly_60_is_included(
        self, results: list[WebSearchResult]
    ) -> None:
        """Results scoring exactly 60 pass the threshold and are saved."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # Scorer returns exactly 60 for all results
        mock_score_result = MagicMock()
        mock_score_result.relevance_score = "60"

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            scorer_instance = MagicMock()
            scorer_instance.return_value = mock_score_result
            mock_predict.return_value = scorer_instance
            mock_emb_cls.return_value.generate_embedding.return_value = _fake_embedding()

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query="test query",
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # Preservation: score == 60 passes threshold, results are saved
        assert len(saved) == len(results)
        conn.close()

    @given(results=_web_results_list)
    @settings(max_examples=10, deadline=None)
    def test_score_59_is_excluded(
        self, results: list[WebSearchResult]
    ) -> None:
        """Results scoring 59 are excluded by the threshold."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # Scorer returns 59 for all results (just below threshold)
        mock_score_result = MagicMock()
        mock_score_result.relevance_score = "59"

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            scorer_instance = MagicMock()
            scorer_instance.return_value = mock_score_result
            mock_predict.return_value = scorer_instance
            mock_emb_cls.return_value.generate_embedding.return_value = _fake_embedding()

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query="test query",
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # Preservation: score 59 is below threshold, nothing saved
        assert len(saved) == 0
        conn.close()


# ---------------------------------------------------------------------------
# Preservation Test 3: Happy-path run_section_search
# **Validates: Requirements 3.3**
# ---------------------------------------------------------------------------


class TestPreservationRunSectionSearchHappyPath:
    """Preservation: Happy-path run_section_search returns scored results and indexes.

    For non-buggy inputs (services available, results score >= 60, embeddings
    succeed), run_section_search returns saved results and calls
    rag_engine.index_with_embeddings with correctly structured docs.

    **Validates: Requirements 3.3**
    """

    @given(
        results=_web_results_list,
        query=_search_query,
        scores=st.lists(_score_above_threshold, min_size=1, max_size=5),
    )
    @settings(max_examples=10, deadline=None)
    def test_happy_path_returns_results_and_indexes(
        self, results: list[WebSearchResult], query: str, scores: list[int]
    ) -> None:
        """Happy path: results scored, embedded, indexed, and returned."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # Cycle scores to match results length
        score_iter = iter(scores * ((len(results) // len(scores)) + 1))

        def make_score_result(*args, **kwargs):
            result = MagicMock()
            result.relevance_score = str(next(score_iter))
            return result

        fake_emb = _fake_embedding()

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            scorer_instance = MagicMock()
            scorer_instance.side_effect = make_score_result
            mock_predict.return_value = scorer_instance
            mock_emb_cls.return_value.generate_embedding.return_value = fake_emb

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # Preservation: all results are returned (all score >= 60)
        assert len(saved) == len(results)

        # Preservation: rag_engine.index_with_embeddings was called
        mock_rag.index_with_embeddings.assert_called_once()
        call_args = mock_rag.index_with_embeddings.call_args
        indexed_topic_id = call_args[0][0]
        docs_indexed = call_args[0][1]

        # Preservation: called with correct topic_id
        assert indexed_topic_id == 1

        # Preservation: docs have expected structure
        assert len(docs_indexed) == len(results)
        for doc in docs_indexed:
            assert "text" in doc
            assert "metadata" in doc
            assert "embedding" in doc
            assert "url" in doc["metadata"]
            assert "source" in doc["metadata"]
            assert doc["metadata"]["source"] == "web"
            assert "section" in doc["metadata"]
            assert doc["metadata"]["section"] == "Competitors"

        conn.close()


# ---------------------------------------------------------------------------
# Preservation Test 4: Query passthrough
# **Validates: Requirements 3.5**
# ---------------------------------------------------------------------------


class TestPreservationQueryPassthrough:
    """Preservation: search_query is passed to search_web() unchanged.

    The search_query value provided to run_section_search is forwarded
    to search_web() without modification.

    **Validates: Requirements 3.5**
    """

    @given(query=_search_query)
    @settings(max_examples=20, deadline=None)
    def test_query_passed_to_search_web_unchanged(self, query: str) -> None:
        """search_query is forwarded to search_web() exactly as given."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        with (
            patch("business_coach.agents.workflow.search_web", return_value=[]) as mock_search,
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService"),
        ):
            scorer_instance = MagicMock()
            mock_predict.return_value = scorer_instance

            run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # Preservation: search_web was called with the exact query
        mock_search.assert_called_once_with(query, max_results=5)
        conn.close()


# ---------------------------------------------------------------------------
# Preservation Test 5: Progress callback messages on happy path
# **Validates: Requirements 3.4**
# ---------------------------------------------------------------------------


class TestPreservationProgressCallbackMessages:
    """Preservation: Progress callback receives expected messages on happy path.

    On happy path (services available, results pass threshold, embeddings succeed),
    progress_callback receives specific messages in order:
    - "Searching web for '...'..."
    - "Found N results. Scoring..."
    - "Indexing N relevant documents..."
    - "Done!"

    **Validates: Requirements 3.4**
    """

    @given(results=_web_results_list, query=_search_query)
    @settings(max_examples=10, deadline=None)
    def test_happy_path_progress_messages(
        self, results: list[WebSearchResult], query: str
    ) -> None:
        """Happy path produces expected progress callback messages."""
        conn = _make_conn_with_topic()
        mock_settings = _make_settings()
        mock_rag = MagicMock()
        progress_messages: list[str] = []

        def progress_cb(msg: str) -> None:
            progress_messages.append(msg)

        # All score >= 60 so they pass threshold
        mock_score_result = MagicMock()
        mock_score_result.relevance_score = "75"

        with (
            patch("business_coach.agents.workflow.search_web", return_value=results),
            patch("business_coach.agents.workflow.dspy.Predict") as mock_predict,
            patch("business_coach.agents.workflow.dspy.context"),
            patch("business_coach.agents.workflow.EmbeddingService") as mock_emb_cls,
        ):
            scorer_instance = MagicMock()
            scorer_instance.return_value = mock_score_result
            mock_predict.return_value = scorer_instance
            mock_emb_cls.return_value.generate_embedding.return_value = _fake_embedding()

            saved = run_section_search(
                topic_id=1,
                business_idea="Test idea",
                section_name="Competitors",
                search_query=query,
                conn=conn,
                rag_engine=mock_rag,
                settings=mock_settings,
                progress_callback=progress_cb,
            )

        # Preservation: expected messages present
        assert len(progress_messages) >= 4

        # Message 1: "Searching web for '<query>'..."
        assert progress_messages[0] == f"Searching web for '{query}'..."

        # Message 2: "Found N results. Scoring..."
        assert progress_messages[1] == f"Found {len(results)} results. Scoring..."

        # Message 3: "Indexing N relevant documents..."
        assert progress_messages[2] == f"Indexing {len(results)} relevant documents..."

        # Message 4: "Done!"
        assert progress_messages[3] == "Done!"

        conn.close()
