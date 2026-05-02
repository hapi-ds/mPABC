"""Property-based tests for markdown-to-LaTeX conversion.

Tests the markdown_to_latex() function for element preservation,
special character escaping, and round-trip structural equivalence.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.export.latex_exporter import markdown_to_latex

# ---------------------------------------------------------------------------
# Strategies — safe text generators that avoid markdown/LaTeX syntax chars
# ---------------------------------------------------------------------------

# Safe alphabet for generated text content: letters, digits, spaces only.
# Avoids *, #, |, `, -, &, %, $, _, {, }, ~, ^ which interfere with parsing.
_SAFE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

_safe_word = st.text(
    alphabet=_SAFE_ALPHABET,
    min_size=1,
    max_size=30,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# Strategy for generating multiple list items
_list_items = st.lists(_safe_word, min_size=1, max_size=5)


# ---------------------------------------------------------------------------
# Property 1: Markdown-to-LaTeX element preservation
# Feature: bc-improvements, Property 1: Markdown-to-LaTeX element preservation
# ---------------------------------------------------------------------------


class TestMarkdownToLatexElementPreservation:
    """Property 1: Markdown-to-LaTeX element preservation.

    For any markdown document containing headings, bold, italic, unordered lists,
    and ordered lists, converting with markdown_to_latex() SHALL produce LaTeX
    output containing the corresponding LaTeX constructs with matching text content.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
    """

    @given(heading_text=_safe_word)
    @settings(max_examples=100)
    def test_heading_converts_to_section(self, heading_text: str) -> None:
        """## heading → \\section{heading} in LaTeX output."""
        markdown = f"## {heading_text}"
        result = markdown_to_latex(markdown)
        expected = f"\\section{{{heading_text}}}"
        assert expected in result, (
            f"Expected '\\section{{{heading_text}}}' in output, got: {result}"
        )

    @given(heading_text=_safe_word)
    @settings(max_examples=100)
    def test_subheading_converts_to_subsection(self, heading_text: str) -> None:
        """### heading → \\subsection{heading} in LaTeX output."""
        markdown = f"### {heading_text}"
        result = markdown_to_latex(markdown)
        expected = f"\\subsection{{{heading_text}}}"
        assert expected in result, (
            f"Expected '\\subsection{{{heading_text}}}' in output, got: {result}"
        )

    @given(bold_text=_safe_word)
    @settings(max_examples=100)
    def test_bold_converts_to_textbf(self, bold_text: str) -> None:
        """**text** → \\textbf{text} in LaTeX output."""
        markdown = f"**{bold_text}**"
        result = markdown_to_latex(markdown)
        expected = f"\\textbf{{{bold_text}}}"
        assert expected in result, (
            f"Expected '\\textbf{{{bold_text}}}' in output, got: {result}"
        )

    @given(italic_text=_safe_word)
    @settings(max_examples=100)
    def test_italic_converts_to_textit(self, italic_text: str) -> None:
        """*text* → \\textit{text} in LaTeX output."""
        markdown = f"*{italic_text}*"
        result = markdown_to_latex(markdown)
        expected = f"\\textit{{{italic_text}}}"
        assert expected in result, (
            f"Expected '\\textit{{{italic_text}}}' in output, got: {result}"
        )

    @given(items=_list_items)
    @settings(max_examples=100)
    def test_unordered_list_converts_to_itemize(self, items: list[str]) -> None:
        """- item → \\begin{itemize} and \\item in LaTeX output."""
        markdown = "\n".join(f"- {item}" for item in items)
        result = markdown_to_latex(markdown)
        assert "\\begin{itemize}" in result, (
            f"Expected '\\begin{{itemize}}' in output, got: {result}"
        )
        assert "\\end{itemize}" in result, (
            f"Expected '\\end{{itemize}}' in output, got: {result}"
        )
        for item in items:
            assert f"\\item {item}" in result, (
                f"Expected '\\item {item}' in output, got: {result}"
            )

    @given(items=_list_items)
    @settings(max_examples=100)
    def test_ordered_list_converts_to_enumerate(self, items: list[str]) -> None:
        """1. item → \\begin{enumerate} and \\item in LaTeX output."""
        markdown = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
        result = markdown_to_latex(markdown)
        assert "\\begin{enumerate}" in result, (
            f"Expected '\\begin{{enumerate}}' in output, got: {result}"
        )
        assert "\\end{enumerate}" in result, (
            f"Expected '\\end{{enumerate}}' in output, got: {result}"
        )
        for item in items:
            assert f"\\item {item}" in result, (
                f"Expected '\\item {item}' in output, got: {result}"
            )


# ---------------------------------------------------------------------------
# Property 2: LaTeX special character escaping
# Feature: bc-improvements, Property 2: LaTeX special character escaping
# ---------------------------------------------------------------------------

# LaTeX special characters and their expected escaped forms
_SPECIAL_CHARS = ["&", "%", "$", "#", "_", "{", "}", "~", "^"]

_ESCAPE_MAP = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Strategy: generate text with random special characters interspersed
_text_with_special_chars = st.text(
    alphabet=st.sampled_from(
        list("abcdefghijklmnopqrstuvwxyz ") + _SPECIAL_CHARS
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: any(c in s for c in _SPECIAL_CHARS) and s.strip() != "")


class TestLatexSpecialCharacterEscaping:
    """Property 2: LaTeX special character escaping.

    For any string containing LaTeX special characters, markdown_to_latex()
    SHALL escape every occurrence so that the output contains no unescaped
    special characters outside of LaTeX commands.

    **Validates: Requirements 2.7**
    """

    @given(text=_text_with_special_chars)
    @settings(max_examples=100)
    def test_special_characters_are_escaped(self, text: str) -> None:
        """All LaTeX special characters are properly escaped in output."""
        result = markdown_to_latex(text)

        # For each special character in the input, verify it's escaped in output
        for char in _SPECIAL_CHARS:
            if char not in text:
                continue

            expected_escape = _ESCAPE_MAP[char]
            count_in_input = text.count(char)

            # Count occurrences of the escaped form in output
            count_escaped = result.count(expected_escape)

            assert count_escaped >= count_in_input, (
                f"Character '{char}' appears {count_in_input} time(s) in input "
                f"but escaped form '{expected_escape}' appears only "
                f"{count_escaped} time(s) in output.\n"
                f"Input: {text!r}\nOutput: {result!r}"
            )

    @given(text=_text_with_special_chars)
    @settings(max_examples=100)
    def test_no_unescaped_special_chars_in_output(self, text: str) -> None:
        """No raw special characters remain unescaped in the output (outside LaTeX commands)."""
        result = markdown_to_latex(text)

        # Remove known LaTeX escape sequences to check for raw chars
        cleaned = result
        # Remove multi-char escapes first
        cleaned = cleaned.replace(r"\textasciitilde{}", "")
        cleaned = cleaned.replace(r"\textasciicircum{}", "")
        # Remove single-char escapes (e.g., \&, \%, \$, \#, \_, \{, \})
        for char in ["&", "%", "$", "#", "_", "{", "}"]:
            cleaned = cleaned.replace(f"\\{char}", "")

        # Now check that none of the special chars remain raw
        for char in _SPECIAL_CHARS:
            if char in text:
                assert char not in cleaned, (
                    f"Unescaped '{char}' found in output after removing escape sequences.\n"
                    f"Input: {text!r}\nOutput: {result!r}\nCleaned: {cleaned!r}"
                )


# ---------------------------------------------------------------------------
# Property 3: Markdown-to-LaTeX round-trip structural equivalence
# Feature: bc-improvements, Property 3: Markdown-to-LaTeX round-trip structural equivalence
# ---------------------------------------------------------------------------


def _extract_markdown_structure(text: str) -> list[tuple[str, str]]:
    """Extract semantic structure from markdown text.

    Returns a list of (element_type, text_content) tuples.
    Element types: 'section', 'subsection', 'unordered_item', 'ordered_item', 'paragraph'.
    """
    import re

    structure: list[tuple[str, str]] = []
    lines = text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            structure.append(("subsection", stripped[4:]))
        elif stripped.startswith("## "):
            structure.append(("section", stripped[3:]))
        elif re.match(r"^[-*]\s+", stripped):
            item_text = re.sub(r"^[-*]\s+", "", stripped)
            structure.append(("unordered_item", item_text))
        elif re.match(r"^\d+\.\s+", stripped):
            item_text = re.sub(r"^\d+\.\s+", "", stripped)
            structure.append(("ordered_item", item_text))
        else:
            structure.append(("paragraph", stripped))

    return structure


def _extract_latex_structure(text: str) -> list[tuple[str, str]]:
    """Extract semantic structure from LaTeX text.

    Returns a list of (element_type, text_content) tuples.
    Element types: 'section', 'subsection', 'unordered_item', 'ordered_item', 'paragraph'.
    """
    import re

    structure: list[tuple[str, str]] = []
    lines = text.split("\n")

    # Track whether we're inside an itemize or enumerate environment
    in_itemize = False
    in_enumerate = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip environment markers
        if stripped in (r"\begin{itemize}", r"\end{itemize}"):
            in_itemize = stripped == r"\begin{itemize}"
            continue
        if stripped in (r"\begin{enumerate}", r"\end{enumerate}"):
            in_enumerate = stripped == r"\begin{enumerate}"
            continue

        # Section commands
        section_match = re.match(r"\\section\{(.+?)\}", stripped)
        if section_match:
            structure.append(("section", section_match.group(1)))
            continue

        subsection_match = re.match(r"\\subsection\{(.+?)\}", stripped)
        if subsection_match:
            structure.append(("subsection", subsection_match.group(1)))
            continue

        # List items
        item_match = re.match(r"\\item\s+(.*)", stripped)
        if item_match:
            item_text = item_match.group(1)
            if in_itemize:
                structure.append(("unordered_item", item_text))
            elif in_enumerate:
                structure.append(("ordered_item", item_text))
            continue

        # Plain text (paragraph)
        if not stripped.startswith("\\"):
            structure.append(("paragraph", stripped))

    return structure


# Strategy: generate a structured markdown document with safe text
_structured_markdown = st.builds(
    lambda sections, items, paragraphs: "\n\n".join(
        [f"## {s}" for s in sections]
        + ["\n".join(f"- {item}" for item in items)]
        + [p for p in paragraphs]
    ),
    sections=st.lists(_safe_word, min_size=1, max_size=3),
    items=st.lists(_safe_word, min_size=1, max_size=3),
    paragraphs=st.lists(_safe_word, min_size=1, max_size=3),
)


class TestMarkdownToLatexRoundTripStructure:
    """Property 3: Markdown-to-LaTeX round-trip structural equivalence.

    For any structured markdown document, converting to LaTeX and extracting
    the semantic structure SHALL produce a structure equivalent to the semantic
    structure extracted from the original markdown.

    **Validates: Requirements 2.8**
    """

    @given(markdown_doc=_structured_markdown)
    @settings(max_examples=100)
    def test_structural_equivalence(self, markdown_doc: str) -> None:
        """Semantic structure is preserved through markdown-to-LaTeX conversion."""
        # Extract structure from original markdown
        md_structure = _extract_markdown_structure(markdown_doc)

        # Convert to LaTeX
        latex_output = markdown_to_latex(markdown_doc)

        # Extract structure from LaTeX output
        latex_structure = _extract_latex_structure(latex_output)

        # Compare element types and content
        assert len(md_structure) == len(latex_structure), (
            f"Structure length mismatch: markdown has {len(md_structure)} elements, "
            f"LaTeX has {len(latex_structure)} elements.\n"
            f"Markdown structure: {md_structure}\n"
            f"LaTeX structure: {latex_structure}\n"
            f"Input:\n{markdown_doc}\n\nOutput:\n{latex_output}"
        )

        for i, (md_elem, latex_elem) in enumerate(zip(md_structure, latex_structure)):
            md_type, md_text = md_elem
            latex_type, latex_text = latex_elem

            assert md_type == latex_type, (
                f"Element {i} type mismatch: markdown='{md_type}', latex='{latex_type}'.\n"
                f"Markdown structure: {md_structure}\n"
                f"LaTeX structure: {latex_structure}"
            )

            assert md_text == latex_text, (
                f"Element {i} text mismatch: markdown='{md_text}', latex='{latex_text}'.\n"
                f"Markdown structure: {md_structure}\n"
                f"LaTeX structure: {latex_structure}"
            )
