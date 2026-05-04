"""Unit tests for LaTeX exporter edge cases.

Tests preamble structure, empty input handling, and bibliography
conditional inclusion.

Validates: Requirements 1.4, 1.5, 3.2, 3.4
"""

import tempfile
from pathlib import Path

from business_coach.db.models import PlanSection, WebSearchResult
from business_coach.export.latex_exporter import (
    _build_preamble,
    export_canvas_latex,
    export_plan_latex,
    export_voices_latex,
)


class TestPreambleStructure:
    """Test that the preamble contains required LaTeX document class and packages.

    Requirements: 1.4
    """

    def test_preamble_contains_documentclass_article(self) -> None:
        """Preamble starts with \\documentclass{article}."""
        preamble = _build_preamble("Test Title")
        assert r"\documentclass{article}" in preamble

    def test_preamble_contains_inputenc_package(self) -> None:
        """Preamble includes \\usepackage[utf8]{inputenc}."""
        preamble = _build_preamble("Test Title")
        assert r"\usepackage[utf8]{inputenc}" in preamble

    def test_preamble_contains_fontenc_package(self) -> None:
        """Preamble includes \\usepackage[T1]{fontenc}."""
        preamble = _build_preamble("Test Title")
        assert r"\usepackage[T1]{fontenc}" in preamble

    def test_preamble_contains_geometry_package(self) -> None:
        """Preamble includes \\usepackage{geometry}."""
        preamble = _build_preamble("Test Title")
        assert r"\usepackage{geometry}" in preamble

    def test_preamble_contains_hyperref_package(self) -> None:
        """Preamble includes \\usepackage{hyperref}."""
        preamble = _build_preamble("Test Title")
        assert r"\usepackage{hyperref}" in preamble

    def test_preamble_contains_begin_document(self) -> None:
        """Preamble includes \\begin{document} and \\maketitle."""
        preamble = _build_preamble("Test Title")
        assert r"\begin{document}" in preamble
        assert r"\maketitle" in preamble

    def test_preamble_contains_title(self) -> None:
        """Preamble includes the \\title{} command with the given title."""
        preamble = _build_preamble("My Business Plan")
        assert r"\title{My Business Plan}" in preamble


class TestEmptyInputHandling:
    """Test that empty input produces no file and returns a warning path.

    Requirements: 1.5
    """

    def test_empty_canvas_elements_produces_no_file(self) -> None:
        """Empty canvas elements list returns empty Path and creates no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = export_canvas_latex("TestTopic", [], output_dir)

            assert result == Path("")
            # No .tex files should exist
            tex_files = list(output_dir.glob("*.tex"))
            assert len(tex_files) == 0

    def test_empty_voices_produces_no_file(self) -> None:
        """Empty voices list returns empty Path and creates no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = export_voices_latex("TestTopic", [], output_dir)

            assert result == Path("")
            tex_files = list(output_dir.glob("*.tex"))
            assert len(tex_files) == 0

    def test_empty_plan_sections_produces_no_file(self) -> None:
        """Empty plan sections list returns empty Path and creates no file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = export_plan_latex("TestTopic", [], output_dir)

            assert result == Path("")
            tex_files = list(output_dir.glob("*.tex"))
            assert len(tex_files) == 0


class TestBibliographyConditionalInclusion:
    """Test bibliography inclusion/exclusion based on search results.

    Requirements: 3.2, 3.4
    """

    def test_plan_with_search_results_includes_addbibresource(self) -> None:
        """When search results are provided, \\addbibresource appears in the .tex file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Our business plan summary.",
                )
            ]
            search_results = [
                WebSearchResult(
                    url="https://example.com/article",
                    title="Example Article",
                    snippet="An example snippet.",
                )
            ]

            result_path = export_plan_latex("TestTopic", sections, output_dir, search_results=search_results)

            assert result_path != Path("")
            tex_content = result_path.read_text(encoding="utf-8")
            assert r"\addbibresource{" in tex_content

    def test_plan_with_search_results_includes_printbibliography(self) -> None:
        """When search results are provided, \\printbibliography appears in the .tex file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Market Analysis",
                    content="Market analysis content.",
                )
            ]
            search_results = [
                WebSearchResult(
                    url="https://example.com/market",
                    title="Market Report",
                    snippet="Market data snippet.",
                )
            ]

            result_path = export_plan_latex("TestTopic", sections, output_dir, search_results=search_results)

            assert result_path != Path("")
            tex_content = result_path.read_text(encoding="utf-8")
            assert r"\printbibliography" in tex_content

    def test_plan_with_search_results_creates_bib_file(self) -> None:
        """When search results are provided, a companion .bib file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Summary content.",
                )
            ]
            search_results = [
                WebSearchResult(
                    url="https://example.com/ref",
                    title="Reference Article",
                    snippet="Reference snippet.",
                )
            ]

            export_plan_latex("TestTopic", sections, output_dir, search_results=search_results)

            bib_files = list(output_dir.glob("*.bib"))
            assert len(bib_files) == 1

    def test_plan_without_search_results_omits_addbibresource(self) -> None:
        """When no search results, \\addbibresource does NOT appear in the .tex file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Summary without references.",
                )
            ]

            result_path = export_plan_latex("TestTopic", sections, output_dir)

            assert result_path != Path("")
            tex_content = result_path.read_text(encoding="utf-8")
            assert r"\addbibresource{" not in tex_content

    def test_plan_without_search_results_omits_printbibliography(self) -> None:
        """When no search results, \\printbibliography does NOT appear in the .tex file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Summary without references.",
                )
            ]

            result_path = export_plan_latex("TestTopic", sections, output_dir)

            assert result_path != Path("")
            tex_content = result_path.read_text(encoding="utf-8")
            assert r"\printbibliography" not in tex_content

    def test_plan_without_search_results_creates_no_bib_file(self) -> None:
        """When no search results, no .bib file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            sections = [
                PlanSection(
                    topic_id=1,
                    section_name="Executive Summary",
                    content="Summary without references.",
                )
            ]

            export_plan_latex("TestTopic", sections, output_dir)

            bib_files = list(output_dir.glob("*.bib"))
            assert len(bib_files) == 0
