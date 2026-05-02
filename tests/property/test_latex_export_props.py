"""Property-based tests for LaTeX export content completeness.

Tests the export_canvas_latex(), export_voices_latex(), and export_plan_latex()
functions for content completeness and section ordering.

Validates: Requirements 1.1, 1.2, 1.3
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.db.models import CanvasElement, PlanSection, VoicePersona
from business_coach.export.latex_exporter import (
    PLAN_SECTION_ORDER,
    export_canvas_latex,
    export_plan_latex,
    export_voices_latex,
)

# ---------------------------------------------------------------------------
# Strategies — safe text generators avoiding LaTeX special chars and markdown
# ---------------------------------------------------------------------------

# Safe alphabet: letters, digits, spaces only.
# Avoids *, #, |, `, -, &, %, $, _, {, }, ~, ^ which interfere with parsing.
_SAFE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

_safe_text = st.text(
    alphabet=_SAFE_ALPHABET,
    min_size=3,
    max_size=40,
).map(lambda s: s.strip()).filter(lambda s: len(s) >= 3)

# CanvasElement strategy
_canvas_element_strategy = st.builds(
    lambda name, content: CanvasElement(
        topic_id=1,
        element_name=name,
        content=content,
    ),
    name=_safe_text,
    content=_safe_text,
)

_canvas_elements_list = st.lists(
    _canvas_element_strategy,
    min_size=1,
    max_size=8,
)

# VoicePersona strategy
_voice_persona_strategy = st.builds(
    lambda name, description, style: VoicePersona(
        topic_id=1,
        name=name,
        description=description,
        communication_style=style,
    ),
    name=_safe_text,
    description=_safe_text,
    style=_safe_text,
)

_voices_list = st.lists(
    _voice_persona_strategy,
    min_size=1,
    max_size=6,
)

# PlanSection strategy using standard section names in shuffled order
_plan_section_strategy = st.builds(
    lambda section_name, content: PlanSection(
        topic_id=1,
        section_name=section_name,
        content=content,
    ),
    section_name=st.just("placeholder"),  # overridden in test
    content=_safe_text,
)


# Strategy for generating plan sections with standard names in random order
@st.composite
def _plan_sections_shuffled(draw: st.DrawFn) -> list[PlanSection]:
    """Generate PlanSection list with standard names in shuffled order."""
    # Pick a subset of standard section names (at least 2)
    num_sections = draw(st.integers(min_value=2, max_value=len(PLAN_SECTION_ORDER)))
    chosen_names = PLAN_SECTION_ORDER[:num_sections]

    sections = []
    for name in chosen_names:
        content = draw(_safe_text)
        sections.append(
            PlanSection(topic_id=1, section_name=name, content=content)
        )

    # Use hypothesis permutations to shuffle (avoids random module warning)
    indices = list(range(len(sections)))
    shuffled_indices = draw(st.permutations(indices))
    return [sections[i] for i in shuffled_indices]


# ---------------------------------------------------------------------------
# Property 6: Canvas export content completeness
# Feature: bc-improvements, Property 6: Canvas export content completeness
# ---------------------------------------------------------------------------


class TestCanvasExportContentCompleteness:
    """Property 6: Canvas export content completeness.

    For any non-empty list of CanvasElement objects, export_canvas_latex() SHALL
    produce a .tex file whose content contains the element_name of every input
    element, and the LaTeX-converted content of every input element.

    **Validates: Requirements 1.1**
    """

    @given(elements=_canvas_elements_list)
    @settings(max_examples=100)
    def test_all_element_names_present(
        self, elements: list[CanvasElement], tmp_path_factory: object
    ) -> None:
        """All canvas element names appear in the generated .tex file."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_canvas_latex("TestTopic", elements, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            for element in elements:
                assert element.element_name in tex_content, (
                    f"Element name '{element.element_name}' not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )

    @given(elements=_canvas_elements_list)
    @settings(max_examples=100)
    def test_all_element_content_present(
        self, elements: list[CanvasElement]
    ) -> None:
        """All canvas element content appears in the generated .tex file."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_canvas_latex("TestTopic", elements, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            for element in elements:
                # Content is safe text (no special chars), so it should appear as-is
                assert element.content in tex_content, (
                    f"Element content '{element.content}' not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )


# ---------------------------------------------------------------------------
# Property 7: Voices export content completeness
# Feature: bc-improvements, Property 7: Voices export content completeness
# ---------------------------------------------------------------------------


class TestVoicesExportContentCompleteness:
    """Property 7: Voices export content completeness.

    For any non-empty list of VoicePersona objects, export_voices_latex() SHALL
    produce a .tex file whose content contains the name, description, and
    communication_style of every input persona.

    **Validates: Requirements 1.2**
    """

    @given(voices=_voices_list)
    @settings(max_examples=100)
    def test_all_persona_names_present(
        self, voices: list[VoicePersona]
    ) -> None:
        """All persona names appear in the generated .tex file."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_voices_latex("TestTopic", voices, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            for persona in voices:
                assert persona.name in tex_content, (
                    f"Persona name '{persona.name}' not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )

    @given(voices=_voices_list)
    @settings(max_examples=100)
    def test_all_persona_descriptions_present(
        self, voices: list[VoicePersona]
    ) -> None:
        """All persona descriptions appear in the generated .tex file."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_voices_latex("TestTopic", voices, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            for persona in voices:
                assert persona.description in tex_content, (
                    f"Persona description '{persona.description}' not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )

    @given(voices=_voices_list)
    @settings(max_examples=100)
    def test_all_persona_styles_present(
        self, voices: list[VoicePersona]
    ) -> None:
        """All persona communication styles appear in the generated .tex file."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_voices_latex("TestTopic", voices, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            for persona in voices:
                assert persona.communication_style in tex_content, (
                    f"Persona style '{persona.communication_style}' not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )


# ---------------------------------------------------------------------------
# Property 8: Plan section ordering
# Feature: bc-improvements, Property 8: Plan section ordering
# ---------------------------------------------------------------------------


class TestPlanSectionOrdering:
    """Property 8: Plan section ordering.

    For any list of PlanSection objects provided in arbitrary order,
    export_plan_latex() SHALL produce a .tex file where sections appear in
    the standard order: Executive Summary, Company Description, Market Analysis,
    Organization & Management, Service or Product Line, Marketing & Sales,
    Funding Request, Financial Projections, Appendix.

    **Validates: Requirements 1.3**
    """

    @given(sections=_plan_sections_shuffled())
    @settings(max_examples=100)
    def test_sections_appear_in_standard_order(
        self, sections: list[PlanSection]
    ) -> None:
        """Plan sections appear in standard order regardless of input order."""
        import tempfile
        from pathlib import Path

        from business_coach.export.latex_exporter import _escape_latex_special_chars

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result_path = export_plan_latex("TestTopic", sections, output_dir)

            assert result_path != Path(""), "Expected a file to be generated"
            tex_content = result_path.read_text(encoding="utf-8")

            # Find positions of each section name in the output.
            # Section names may contain LaTeX special chars (e.g. & in
            # "Organization & Management") which get escaped in the .tex output.
            section_positions: list[tuple[int, str]] = []
            for section in sections:
                escaped_name = _escape_latex_special_chars(section.section_name)
                pos = tex_content.find(escaped_name)
                assert pos != -1, (
                    f"Section '{section.section_name}' (escaped: '{escaped_name}') "
                    f"not found in .tex output.\n"
                    f"Output:\n{tex_content[:500]}"
                )
                section_positions.append((pos, section.section_name))

            # Sort by position to get the actual order in the document
            section_positions.sort(key=lambda x: x[0])
            actual_order = [name for _, name in section_positions]

            # Build expected order from PLAN_SECTION_ORDER for the sections present
            expected_order = [
                name for name in PLAN_SECTION_ORDER
                if name in [s.section_name for s in sections]
            ]

            assert actual_order == expected_order, (
                f"Section order mismatch.\n"
                f"Expected: {expected_order}\n"
                f"Actual:   {actual_order}\n"
                f"Input order: {[s.section_name for s in sections]}"
            )
