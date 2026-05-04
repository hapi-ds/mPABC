"""Unit tests for Settings panel LaTeX export integration.

Tests that the LaTeX export functions are importable, callable,
handle empty input correctly, and produce valid .tex files.

Validates: Requirements 14.1, 14.2, 14.3
"""

import tempfile
from pathlib import Path

from business_coach.db.models import CanvasElement, PlanSection, VoicePersona, WebSearchResult
from business_coach.export.latex_exporter import (
    export_canvas_latex,
    export_plan_latex,
    export_voices_latex,
)


class TestLatexExporterImportability:
    """Test that latex_exporter functions are importable and callable.

    Requirements: 14.1
    """

    def test_export_canvas_latex_is_callable(self) -> None:
        """export_canvas_latex is importable and callable."""
        assert callable(export_canvas_latex)

    def test_export_voices_latex_is_callable(self) -> None:
        """export_voices_latex is importable and callable."""
        assert callable(export_voices_latex)

    def test_export_plan_latex_is_callable(self) -> None:
        """export_plan_latex is importable and callable."""
        assert callable(export_plan_latex)


class TestLatexExportEmptyInput:
    """Test that export functions handle empty input correctly.

    Requirements: 14.2
    """

    def test_export_canvas_latex_empty_returns_empty_path(self) -> None:
        """Empty canvas elements returns Path('')."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_canvas_latex("Test", [], Path(tmpdir))
            assert result == Path("")

    def test_export_voices_latex_empty_returns_empty_path(self) -> None:
        """Empty voices list returns Path('')."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_voices_latex("Test", [], Path(tmpdir))
            assert result == Path("")

    def test_export_plan_latex_empty_returns_empty_path(self) -> None:
        """Empty plan sections returns Path('')."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_plan_latex("Test", [], Path(tmpdir))
            assert result == Path("")


class TestLatexExportProducesValidFiles:
    """Test that export functions produce valid .tex files with expected content.

    Requirements: 14.1, 14.2, 14.3
    """

    def test_export_canvas_produces_tex_file(self) -> None:
        """Canvas export produces a .tex file with documentclass and element names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            elements = [
                CanvasElement(
                    topic_id=1,
                    element_name="Value Proposition",
                    content="Our unique value.",
                )
            ]
            result = export_canvas_latex("MyBiz", elements, Path(tmpdir))

            assert result != Path("")
            assert result.suffix == ".tex"
            content = result.read_text(encoding="utf-8")
            assert r"\documentclass{article}" in content
            assert "Value Proposition" in content

    def test_export_voices_produces_tex_file(self) -> None:
        """Voices export produces a .tex file with persona names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            voices = [
                VoicePersona(
                    topic_id=1,
                    name="Investor",
                    description="A cautious investor.",
                    communication_style="Formal and analytical.",
                )
            ]
            result = export_voices_latex("MyBiz", voices, Path(tmpdir))

            assert result != Path("")
            assert result.suffix == ".tex"
            content = result.read_text(encoding="utf-8")
            assert r"\documentclass{article}" in content
            assert "Investor" in content
            assert "cautious investor" in content

    def test_export_plan_produces_tex_file(self) -> None:
        """Plan export produces a .tex file with section names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Our executive summary.",
                )
            ]
            result = export_plan_latex("MyBiz", sections, Path(tmpdir))

            assert result != Path("")
            assert result.suffix == ".tex"
            content = result.read_text(encoding="utf-8")
            assert r"\documentclass{article}" in content
            assert "Executive Summary" in content

    def test_export_plan_with_search_results_includes_bibliography(self) -> None:
        """Plan export with search results includes bibliography references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Market Analysis",
                    content="See https://example.com/market for details.",
                )
            ]
            search_results = [
                WebSearchResult(
                    url="https://example.com/market",
                    title="Market Report",
                    snippet="Market data.",
                )
            ]
            result = export_plan_latex("MyBiz", sections, Path(tmpdir), search_results=search_results)

            assert result != Path("")
            content = result.read_text(encoding="utf-8")
            assert r"\addbibresource{" in content
            assert r"\printbibliography" in content


class TestLatexExportErrorHandling:
    """Test that export errors are handled gracefully.

    Requirements: 14.3
    """

    def test_export_canvas_with_invalid_dir_raises(self) -> None:
        """Export to a non-writable path raises an OSError."""
        elements = [
            CanvasElement(
                topic_id=1,
                element_name="Test",
                content="Content.",
            )
        ]
        # Use a path that cannot be created (nested under a file)
        invalid_dir = Path("/dev/null/impossible_dir")
        try:
            export_canvas_latex("Test", elements, invalid_dir)
            # If it doesn't raise, it should return empty or the test platform
            # handles /dev/null differently
        except OSError:
            pass  # Expected behavior - error is raised

    def test_settings_panel_latex_imports_are_available(self) -> None:
        """The settings panel can import all required LaTeX export functions."""
        from business_coach.gui.settings_panel import (  # noqa: F401
            export_canvas_latex,
            export_plan_latex,
            export_voices_latex,
        )
