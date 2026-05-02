"""Unit tests for SpecialistPersona model and SPECIALIST_REGISTRY.

Validates: Requirements 2.1, 2.2, 2.3, 2.5, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

import pytest

from business_coach.agents.specialists import (
    SPECIALIST_REGISTRY,
    SpecialistPersona,
    get_specialist,
)


# Expected canvas element keys (9 total)
CANVAS_ELEMENTS = [
    "Key Partners",
    "Key Activities",
    "Key Resources",
    "Value Propositions",
    "Customer Relationships",
    "Channels",
    "Customer Segments",
    "Cost Structure",
    "Revenue Streams",
]

# Expected plan section keys (9 total)
PLAN_SECTIONS = [
    "Executive Summary",
    "Company Description",
    "Market Analysis",
    "Organization & Management",
    "Service or Product Line",
    "Marketing & Sales",
    "Funding Request",
    "Financial Projections",
    "Appendix",
]


class TestRegistryStructure:
    """Test SPECIALIST_REGISTRY structure and completeness."""

    def test_registry_is_a_dict(self) -> None:
        """Validates: Requirement 2.5 — extensible data structure."""
        assert isinstance(SPECIALIST_REGISTRY, dict)

    def test_registry_contains_all_canvas_element_keys(self) -> None:
        """Validates: Requirement 2.1 — all 9 canvas elements mapped."""
        for element in CANVAS_ELEMENTS:
            assert element in SPECIALIST_REGISTRY, f"Missing canvas element: {element}"

    def test_registry_contains_all_plan_section_keys(self) -> None:
        """Validates: Requirement 2.2 — all 9 plan sections mapped."""
        for section in PLAN_SECTIONS:
            assert section in SPECIALIST_REGISTRY, f"Missing plan section: {section}"

    def test_registry_contains_voice_personas_key(self) -> None:
        """Validates: Requirement 2.3 — voice persona generation mapped."""
        assert "voice_personas" in SPECIALIST_REGISTRY

    def test_all_registry_specialists_have_unique_ids(self) -> None:
        """Each specialist in the registry must have a unique ID."""
        ids = [persona.id for persona in SPECIALIST_REGISTRY.values()]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_registry_values_are_specialist_personas(self) -> None:
        """All registry values must be SpecialistPersona instances."""
        for key, persona in SPECIALIST_REGISTRY.items():
            assert isinstance(persona, SpecialistPersona), f"Value for '{key}' is not a SpecialistPersona"


class TestFinancialProjectionsPrompt:
    """Test Financial Projections specialist prompt quality."""

    def test_contains_revenue_models(self) -> None:
        """Validates: Requirement 9.1"""
        prompt = SPECIALIST_REGISTRY["Financial Projections"].system_prompt.lower()
        assert "revenue models" in prompt

    def test_contains_cost_structures(self) -> None:
        """Validates: Requirement 9.1"""
        prompt = SPECIALIST_REGISTRY["Financial Projections"].system_prompt.lower()
        assert "cost structures" in prompt

    def test_contains_break_even(self) -> None:
        """Validates: Requirement 9.1"""
        prompt = SPECIALIST_REGISTRY["Financial Projections"].system_prompt.lower()
        assert "break-even" in prompt

    def test_contains_financial_forecasting(self) -> None:
        """Validates: Requirement 9.1"""
        prompt = SPECIALIST_REGISTRY["Financial Projections"].system_prompt.lower()
        assert "financial forecasting" in prompt


class TestMarketingSalesPrompt:
    """Test Marketing & Sales specialist prompt quality."""

    def test_contains_go_to_market(self) -> None:
        """Validates: Requirement 9.2"""
        prompt = SPECIALIST_REGISTRY["Marketing & Sales"].system_prompt.lower()
        assert "go-to-market" in prompt

    def test_contains_customer_acquisition(self) -> None:
        """Validates: Requirement 9.2"""
        prompt = SPECIALIST_REGISTRY["Marketing & Sales"].system_prompt.lower()
        assert "customer acquisition" in prompt

    def test_contains_pricing_strategy(self) -> None:
        """Validates: Requirement 9.2"""
        prompt = SPECIALIST_REGISTRY["Marketing & Sales"].system_prompt.lower()
        assert "pricing strategy" in prompt

    def test_contains_sales_funnels(self) -> None:
        """Validates: Requirement 9.2"""
        prompt = SPECIALIST_REGISTRY["Marketing & Sales"].system_prompt.lower()
        assert "sales funnels" in prompt


class TestExecutiveSummaryPrompt:
    """Test Executive Summary specialist prompt quality."""

    def test_contains_high_level_vision(self) -> None:
        """Validates: Requirement 9.3"""
        prompt = SPECIALIST_REGISTRY["Executive Summary"].system_prompt.lower()
        assert "high-level vision" in prompt

    def test_contains_strategic_positioning(self) -> None:
        """Validates: Requirement 9.3"""
        prompt = SPECIALIST_REGISTRY["Executive Summary"].system_prompt.lower()
        assert "strategic positioning" in prompt

    def test_contains_value_propositions(self) -> None:
        """Validates: Requirement 9.3"""
        prompt = SPECIALIST_REGISTRY["Executive Summary"].system_prompt.lower()
        assert "value propositions" in prompt

    def test_contains_investment_readiness(self) -> None:
        """Validates: Requirement 9.3"""
        prompt = SPECIALIST_REGISTRY["Executive Summary"].system_prompt.lower()
        assert "investment readiness" in prompt


class TestMarketAnalysisPrompt:
    """Test Market Analysis specialist prompt quality."""

    def test_contains_industry_trends(self) -> None:
        """Validates: Requirement 9.4"""
        prompt = SPECIALIST_REGISTRY["Market Analysis"].system_prompt.lower()
        assert "industry trends" in prompt

    def test_contains_competitive_landscape(self) -> None:
        """Validates: Requirement 9.4"""
        prompt = SPECIALIST_REGISTRY["Market Analysis"].system_prompt.lower()
        assert "competitive landscape" in prompt

    def test_contains_target_market_sizing(self) -> None:
        """Validates: Requirement 9.4"""
        prompt = SPECIALIST_REGISTRY["Market Analysis"].system_prompt.lower()
        assert "target market sizing" in prompt

    def test_contains_market_entry_barriers(self) -> None:
        """Validates: Requirement 9.4"""
        prompt = SPECIALIST_REGISTRY["Market Analysis"].system_prompt.lower()
        assert "market entry barriers" in prompt


class TestValuePropositionsPrompt:
    """Test Value Propositions specialist prompt quality."""

    def test_contains_customer_pain_points(self) -> None:
        """Validates: Requirement 9.5"""
        prompt = SPECIALIST_REGISTRY["Value Propositions"].system_prompt.lower()
        assert "customer pain points" in prompt

    def test_contains_unique_differentiators(self) -> None:
        """Validates: Requirement 9.5"""
        prompt = SPECIALIST_REGISTRY["Value Propositions"].system_prompt.lower()
        assert "unique differentiators" in prompt

    def test_contains_value_delivery(self) -> None:
        """Validates: Requirement 9.5"""
        prompt = SPECIALIST_REGISTRY["Value Propositions"].domain_description.lower()
        assert "value delivery" in prompt


class TestCostStructurePrompt:
    """Test Cost Structure specialist prompt quality."""

    def test_contains_fixed_and_variable_costs(self) -> None:
        """Validates: Requirement 9.6"""
        prompt = SPECIALIST_REGISTRY["Cost Structure"].system_prompt.lower()
        assert "fixed and variable costs" in prompt

    def test_contains_economies_of_scale(self) -> None:
        """Validates: Requirement 9.6"""
        prompt = SPECIALIST_REGISTRY["Cost Structure"].system_prompt.lower()
        assert "economies of scale" in prompt

    def test_contains_cost_optimization(self) -> None:
        """Validates: Requirement 9.6"""
        prompt = SPECIALIST_REGISTRY["Cost Structure"].system_prompt.lower()
        assert "cost optimization" in prompt


class TestSchemaMigration:
    """Test that init_schema creates the specialist_overrides table.

    Validates: Requirements 8.1, 10.4
    """

    def test_init_schema_creates_specialist_overrides_table(self) -> None:
        """init_schema() should create the specialist_overrides table in an in-memory DB."""
        import sqlite3

        from business_coach.db.schema import init_schema

        conn = sqlite3.connect(":memory:")
        init_schema(conn)

        # Query sqlite_master to verify the table exists
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='specialist_overrides'"
        ).fetchone()
        assert row is not None, "specialist_overrides table was not created"
        assert row[0] == "specialist_overrides"

        # Verify expected columns exist
        cursor = conn.execute("PRAGMA table_info(specialist_overrides)")
        columns = {r[1] for r in cursor.fetchall()}
        expected_columns = {"id", "topic_id", "section_name", "specialist_id", "updated_at"}
        assert expected_columns.issubset(columns), f"Missing columns: {expected_columns - columns}"

        conn.close()


# ---------------------------------------------------------------------------
# Integration tests for specialist usage in generation functions
# Validates: Requirements 4.2, 5.2, 6.2, 8.2
# ---------------------------------------------------------------------------

import json
import sqlite3
from unittest.mock import MagicMock, patch

from business_coach.agents.specialists import SPECIALIST_REGISTRY, get_specialist
from business_coach.agents.workflow import (
    PERSONALITY_PROMPTS,
    generate_canvas_element,
    generate_plan_section,
    generate_voice_personas,
)
from business_coach.db.schema import init_schema


def _make_test_db() -> sqlite3.Connection:
    """Create an in-memory SQLite DB with schema initialized and a test topic."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute("INSERT INTO topics (id, name) VALUES (1, 'Test Topic')")
    conn.commit()
    return conn


class TestGenerateCanvasElementUsesSpecialist:
    """Test that generate_canvas_element applies the correct specialist prompt.

    Validates: Requirement 4.2
    """

    @patch("business_coach.agents.workflow._task_lms", {"canvas": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_canvas_element_uses_correct_specialist(self, mock_predict: MagicMock) -> None:
        """generate_canvas_element should compose prompt with the specialist for the given element."""
        # Set up mock to return a result with generated_content
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Test content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        element_name = "Key Partners"
        expected_specialist = SPECIALIST_REGISTRY[element_name]

        result = generate_canvas_element(
            business_idea="A test idea",
            element_name=element_name,
            conn=conn,
            topic_id=1,
        )

        assert result == "Test content"

        # Verify Predict was called with a signature that had with_instructions applied
        # The signature passed to Predict should have instructions containing the specialist prompt
        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]  # first positional arg to Predict()
        # The signature's instructions should contain the specialist system_prompt
        instructions = signature_arg.__doc__ or ""
        assert expected_specialist.system_prompt in instructions

        conn.close()

    @patch("business_coach.agents.workflow._task_lms", {"canvas": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_canvas_element_includes_personality_prompt(self, mock_predict: MagicMock) -> None:
        """generate_canvas_element should include the personality prompt before the specialist prompt."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        element_name = "Value Propositions"

        generate_canvas_element(
            business_idea="A test idea",
            element_name=element_name,
            conn=conn,
            topic_id=1,
        )

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        # Default personality is "Balanced"
        assert PERSONALITY_PROMPTS["Balanced"] in instructions
        assert SPECIALIST_REGISTRY[element_name].system_prompt in instructions
        # Personality should come before specialist
        personality_pos = instructions.find(PERSONALITY_PROMPTS["Balanced"])
        specialist_pos = instructions.find(SPECIALIST_REGISTRY[element_name].system_prompt)
        assert personality_pos < specialist_pos

        conn.close()


class TestGeneratePlanSectionUsesSpecialist:
    """Test that generate_plan_section applies the correct specialist prompt.

    Validates: Requirement 5.2
    """

    @patch("business_coach.agents.workflow._task_lms", {"plan": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_plan_section_uses_correct_specialist(self, mock_predict: MagicMock) -> None:
        """generate_plan_section should compose prompt with the specialist for the given section."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Plan content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        section_name = "Financial Projections"
        expected_specialist = SPECIALIST_REGISTRY[section_name]

        result = generate_plan_section(
            business_idea="A test idea",
            business_canvas_text="Canvas text",
            personas_text="Personas text",
            section_name=section_name,
            conn=conn,
            topic_id=1,
        )

        assert result == "Plan content"

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        assert expected_specialist.system_prompt in instructions

        conn.close()

    @patch("business_coach.agents.workflow._task_lms", {"plan": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_plan_section_marketing_uses_marketing_specialist(self, mock_predict: MagicMock) -> None:
        """Marketing & Sales section should use the marketing_director specialist."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Marketing content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        section_name = "Marketing & Sales"
        expected_specialist = SPECIALIST_REGISTRY[section_name]

        generate_plan_section(
            business_idea="A test idea",
            business_canvas_text="Canvas text",
            personas_text="Personas text",
            section_name=section_name,
            conn=conn,
            topic_id=1,
        )

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        assert expected_specialist.system_prompt in instructions
        assert "go-to-market" in instructions.lower()

        conn.close()


class TestGenerateVoicePersonasUsesSpecialist:
    """Test that generate_voice_personas applies the voice_personas specialist.

    Validates: Requirement 6.2
    """

    @patch("business_coach.agents.workflow._task_lms", {"voices": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_voice_personas_uses_audience_researcher(self, mock_predict: MagicMock) -> None:
        """generate_voice_personas should use the 'voice_personas' specialist."""
        personas_data = [
            {"name": "Persona 1", "description": "Desc 1", "communication_style": "Style 1"}
        ]
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(personas_json=json.dumps(personas_data))
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        expected_specialist = SPECIALIST_REGISTRY["voice_personas"]

        result = generate_voice_personas(
            business_canvas_text="Canvas text",
            num_personas=1,
            conn=conn,
            topic_id=1,
        )

        assert result == personas_data

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        assert expected_specialist.system_prompt in instructions
        assert "Audience Research" in instructions

        conn.close()


class TestOverridesAppliedDuringGeneration:
    """Test that specialist overrides from the DB are loaded and applied.

    Validates: Requirement 8.2
    """

    @patch("business_coach.agents.workflow._task_lms", {"canvas": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_canvas_element_uses_override_specialist(self, mock_predict: MagicMock) -> None:
        """When an override exists, generate_canvas_element should use the overridden specialist."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Override content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        # Set an override: use the CFO specialist for "Key Partners" instead of the default
        override_specialist = SPECIALIST_REGISTRY["Financial Projections"]
        conn.execute(
            "INSERT INTO specialist_overrides (topic_id, section_name, specialist_id) VALUES (?, ?, ?)",
            (1, "Key Partners", override_specialist.id),
        )
        conn.commit()

        result = generate_canvas_element(
            business_idea="A test idea",
            element_name="Key Partners",
            conn=conn,
            topic_id=1,
        )

        assert result == "Override content"

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        # Should contain the CFO specialist prompt, NOT the partnerships strategist
        assert override_specialist.system_prompt in instructions
        default_specialist = SPECIALIST_REGISTRY["Key Partners"]
        assert default_specialist.system_prompt not in instructions

        conn.close()

    @patch("business_coach.agents.workflow._task_lms", {"plan": MagicMock()})
    @patch("business_coach.agents.workflow.dspy.Predict")
    def test_plan_section_uses_override_specialist(self, mock_predict: MagicMock) -> None:
        """When an override exists, generate_plan_section should use the overridden specialist."""
        mock_agent = MagicMock()
        mock_agent.return_value = MagicMock(generated_content="Override plan content")
        mock_predict.return_value = mock_agent

        conn = _make_test_db()
        # Override "Executive Summary" to use the marketing_director specialist
        override_specialist = SPECIALIST_REGISTRY["Marketing & Sales"]
        conn.execute(
            "INSERT INTO specialist_overrides (topic_id, section_name, specialist_id) VALUES (?, ?, ?)",
            (1, "Executive Summary", override_specialist.id),
        )
        conn.commit()

        result = generate_plan_section(
            business_idea="A test idea",
            business_canvas_text="Canvas text",
            personas_text="Personas text",
            section_name="Executive Summary",
            conn=conn,
            topic_id=1,
        )

        assert result == "Override plan content"

        call_args = mock_predict.call_args
        signature_arg = call_args[0][0]
        instructions = signature_arg.__doc__ or ""
        # Should contain the marketing director prompt, NOT the chief strategist
        assert override_specialist.system_prompt in instructions
        default_specialist = SPECIALIST_REGISTRY["Executive Summary"]
        assert default_specialist.system_prompt not in instructions

        conn.close()


# ---------------------------------------------------------------------------
# Unit tests for settings panel specialist section (SpecialistOverrideRepository)
# Validates: Requirements 7.2, 7.4
# ---------------------------------------------------------------------------

from business_coach.db.repository import SpecialistOverrideRepository


class TestSettingsPanelSpecialistOverrides:
    """Test SpecialistOverrideRepository operations used by the settings panel.

    Validates: Requirements 7.2, 7.4
    """

    def _make_db(self) -> sqlite3.Connection:
        """Create an in-memory SQLite DB with schema and a test topic."""
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        conn.execute("INSERT INTO topics (id, name) VALUES (1, 'Test Topic')")
        conn.commit()
        return conn

    def test_save_and_retrieve_override(self) -> None:
        """Validates: Requirement 7.2 — persisting an override and reading it back."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        repo.save(topic_id=1, section_name="Key Partners", specialist_id="cfo")
        result = repo.get_override(topic_id=1, section_name="Key Partners")

        assert result == "cfo"
        conn.close()

    def test_save_multiple_overrides_and_retrieve_all(self) -> None:
        """Validates: Requirement 7.2 — multiple overrides persisted per topic."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        repo.save(topic_id=1, section_name="Key Partners", specialist_id="cfo")
        repo.save(topic_id=1, section_name="Revenue Streams", specialist_id="marketing_director")

        all_overrides = repo.get_all_overrides(topic_id=1)
        assert all_overrides == {
            "Key Partners": "cfo",
            "Revenue Streams": "marketing_director",
        }
        conn.close()

    def test_save_override_upserts_on_conflict(self) -> None:
        """Validates: Requirement 7.2 — updating an existing override replaces the specialist_id."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        repo.save(topic_id=1, section_name="Key Partners", specialist_id="cfo")
        repo.save(topic_id=1, section_name="Key Partners", specialist_id="marketing_director")

        result = repo.get_override(topic_id=1, section_name="Key Partners")
        assert result == "marketing_director"
        conn.close()

    def test_get_override_returns_none_when_not_set(self) -> None:
        """Validates: Requirement 7.2 — no override returns None."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        result = repo.get_override(topic_id=1, section_name="Key Partners")
        assert result is None
        conn.close()

    def test_delete_override_removes_it(self) -> None:
        """Validates: Requirement 7.4 — deleting an override removes it from the DB."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        repo.save(topic_id=1, section_name="Key Partners", specialist_id="cfo")
        assert repo.get_override(topic_id=1, section_name="Key Partners") == "cfo"

        repo.delete(topic_id=1, section_name="Key Partners")
        assert repo.get_override(topic_id=1, section_name="Key Partners") is None
        conn.close()

    def test_delete_nonexistent_override_does_not_raise(self) -> None:
        """Validates: Requirement 7.4 — deleting a non-existent override is a no-op."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        # Should not raise
        repo.delete(topic_id=1, section_name="Key Partners")
        assert repo.get_override(topic_id=1, section_name="Key Partners") is None
        conn.close()

    def test_delete_only_affects_specified_section(self) -> None:
        """Validates: Requirement 7.4 — deleting one override leaves others intact."""
        conn = self._make_db()
        repo = SpecialistOverrideRepository(conn)

        repo.save(topic_id=1, section_name="Key Partners", specialist_id="cfo")
        repo.save(topic_id=1, section_name="Revenue Streams", specialist_id="marketing_director")

        repo.delete(topic_id=1, section_name="Key Partners")

        assert repo.get_override(topic_id=1, section_name="Key Partners") is None
        assert repo.get_override(topic_id=1, section_name="Revenue Streams") == "marketing_director"
        conn.close()
