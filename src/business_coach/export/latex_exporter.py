"""LaTeX export for mPABS Business Coach.

Provides markdown-to-LaTeX conversion, BibTeX bibliography generation,
and document export functions for canvas, voices, and business plan content.
"""

import logging
import re
from pathlib import Path

from business_coach.db.models import (
    CanvasElement,
    PlanSection,
    VoicePersona,
    WebSearchResult,
)

logger = logging.getLogger(__name__)


def _escape_latex_special_chars(text: str) -> str:
    """Escape LaTeX special characters in plain text.

    Handles: &, %, $, #, _, {, }, ~, ^

    Args:
        text: Plain text that may contain special characters.

    Returns:
        Text with all LaTeX special characters properly escaped.
    """
    # Order matters: backslash is not in the spec list, but we must not
    # double-escape the backslashes we introduce. Process each char individually.
    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    return text


def _process_inline_formatting(line: str) -> str:
    """Apply inline markdown formatting (bold, italic) to a line.

    Processes bold (**text**) before italic (*text*) to avoid conflicts.

    Args:
        line: A single line of text with LaTeX special chars already escaped.

    Returns:
        Line with bold/italic converted to LaTeX commands.
    """
    # Bold: **text** → \textbf{text}
    line = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", line)
    # Italic: *text* → \textit{text}
    line = re.sub(r"\*(.+?)\*", r"\\textit{\1}", line)
    return line


def markdown_to_latex(text: str, heading_offset: int = 0) -> str:
    """Convert markdown-formatted text to LaTeX markup.

    Handles: headings (## → \\section, ### → \\subsection),
    bold (**text** → \\textbf{}), italic (*text* → \\textit{}),
    unordered lists (- item → itemize), ordered lists (1. item → enumerate),
    tables (→ tabular), fenced code blocks (→ verbatim),
    and special character escaping (&, %, $, #, _, {, }, ~, ^).

    Args:
        text: Markdown-formatted string.
        heading_offset: Number of levels to demote headings. 0 means
            ## → \\section, ### → \\subsection (default). 1 means
            ## → \\subsection, ### → \\subsubsection. Useful when
            content is placed inside an existing \\section{}.

    Returns:
        LaTeX-formatted string (body content only, no preamble).
    """
    if not text:
        return ""

    # Heading level mapping based on offset
    _HEADING_COMMANDS = [r"\section", r"\subsection", r"\subsubsection", r"\paragraph"]

    def _heading_cmd(base_level: int) -> str:
        """Return the LaTeX heading command for a given base level + offset.

        base_level 0 = ## (section-level), 1 = ### (subsection-level).
        """
        idx = min(base_level + heading_offset, len(_HEADING_COMMANDS) - 1)
        return _HEADING_COMMANDS[idx]

    lines = text.split("\n")
    output_lines: list[str] = []

    # State tracking
    in_code_block = False
    in_unordered_list = False
    in_ordered_list = False
    in_table = False
    table_col_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- Code block handling (fenced with ```) ---
        if line.strip().startswith("```"):
            if not in_code_block:
                # Close any open environments first
                if in_unordered_list:
                    output_lines.append(r"\end{itemize}")
                    in_unordered_list = False
                if in_ordered_list:
                    output_lines.append(r"\end{enumerate}")
                    in_ordered_list = False
                if in_table:
                    output_lines.append(r"\end{tabular}")
                    in_table = False

                in_code_block = True
                output_lines.append(r"\begin{verbatim}")
            else:
                in_code_block = False
                output_lines.append(r"\end{verbatim}")
            i += 1
            continue

        if in_code_block:
            # Inside code blocks, content passes through verbatim (no escaping)
            output_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # --- Empty line: close open list/table environments ---
        if not stripped:
            if in_unordered_list:
                output_lines.append(r"\end{itemize}")
                in_unordered_list = False
            if in_ordered_list:
                output_lines.append(r"\end{enumerate}")
                in_ordered_list = False
            if in_table:
                output_lines.append(r"\end{tabular}")
                in_table = False
            output_lines.append("")
            i += 1
            continue

        # --- Table detection ---
        # A table row starts with | and ends with |
        if stripped.startswith("|") and stripped.endswith("|"):
            # Check if this is a separator row (e.g., |---|---|)
            if re.match(r"^\|[\s\-:]+(\|[\s\-:]+)+\|$", stripped):
                # Separator row - skip it (already handled in table header)
                i += 1
                continue

            # Parse table cells
            cells = [
                cell.strip() for cell in stripped.split("|")[1:-1]
            ]

            if not in_table:
                # Starting a new table
                # Close any open environments
                if in_unordered_list:
                    output_lines.append(r"\end{itemize}")
                    in_unordered_list = False
                if in_ordered_list:
                    output_lines.append(r"\end{enumerate}")
                    in_ordered_list = False

                table_col_count = len(cells)
                col_spec = "|" + "l|" * table_col_count
                output_lines.append(r"\begin{tabular}{" + col_spec + "}")
                output_lines.append(r"\hline")
                in_table = True

            # Escape and format cells
            escaped_cells = [
                _process_inline_formatting(_escape_latex_special_chars(cell))
                for cell in cells
            ]
            output_lines.append(" & ".join(escaped_cells) + r" \\")
            output_lines.append(r"\hline")
            i += 1
            continue

        # If we were in a table but this line isn't a table row, close it
        if in_table:
            output_lines.append(r"\end{tabular}")
            in_table = False

        # --- Headings ---
        if stripped.startswith("### "):
            # Close any open environments
            if in_unordered_list:
                output_lines.append(r"\end{itemize}")
                in_unordered_list = False
            if in_ordered_list:
                output_lines.append(r"\end{enumerate}")
                in_ordered_list = False

            heading_text = stripped[4:]
            escaped_heading = _escape_latex_special_chars(heading_text)
            escaped_heading = _process_inline_formatting(escaped_heading)
            output_lines.append(_heading_cmd(1) + "{" + escaped_heading + "}")
            i += 1
            continue

        if stripped.startswith("## "):
            # Close any open environments
            if in_unordered_list:
                output_lines.append(r"\end{itemize}")
                in_unordered_list = False
            if in_ordered_list:
                output_lines.append(r"\end{enumerate}")
                in_ordered_list = False

            heading_text = stripped[3:]
            escaped_heading = _escape_latex_special_chars(heading_text)
            escaped_heading = _process_inline_formatting(escaped_heading)
            output_lines.append(_heading_cmd(0) + "{" + escaped_heading + "}")
            i += 1
            continue

        # --- Unordered list items ---
        if re.match(r"^[-*]\s+", stripped):
            if in_ordered_list:
                output_lines.append(r"\end{enumerate}")
                in_ordered_list = False

            if not in_unordered_list:
                output_lines.append(r"\begin{itemize}")
                in_unordered_list = True

            item_text = re.sub(r"^[-*]\s+", "", stripped)
            escaped_item = _escape_latex_special_chars(item_text)
            escaped_item = _process_inline_formatting(escaped_item)
            output_lines.append(r"\item " + escaped_item)
            i += 1
            continue

        # --- Ordered list items ---
        if re.match(r"^\d+\.\s+", stripped):
            if in_unordered_list:
                output_lines.append(r"\end{itemize}")
                in_unordered_list = False

            if not in_ordered_list:
                output_lines.append(r"\begin{enumerate}")
                in_ordered_list = True

            item_text = re.sub(r"^\d+\.\s+", "", stripped)
            escaped_item = _escape_latex_special_chars(item_text)
            escaped_item = _process_inline_formatting(escaped_item)
            output_lines.append(r"\item " + escaped_item)
            i += 1
            continue

        # --- Plain text / paragraph ---
        # Close any open list environments since this is not a list item
        if in_unordered_list:
            output_lines.append(r"\end{itemize}")
            in_unordered_list = False
        if in_ordered_list:
            output_lines.append(r"\end{enumerate}")
            in_ordered_list = False

        # Escape special chars and apply inline formatting
        escaped_line = _escape_latex_special_chars(stripped)
        escaped_line = _process_inline_formatting(escaped_line)
        output_lines.append(escaped_line)
        i += 1

    # Close any remaining open environments at end of input
    if in_code_block:
        output_lines.append(r"\end{verbatim}")
    if in_unordered_list:
        output_lines.append(r"\end{itemize}")
    if in_ordered_list:
        output_lines.append(r"\end{enumerate}")
    if in_table:
        output_lines.append(r"\end{tabular}")

    return "\n".join(output_lines)


def generate_bibtex(
    search_results: list[WebSearchResult],
) -> tuple[str, dict[str, str]]:
    """Generate a BibTeX file string and a URL-to-citekey mapping.

    Each search result produces an ``@misc`` entry with fields for title,
    url, note (snippet), and year (from discovered_date).

    Args:
        search_results: Web search result records from the database.

    Returns:
        A tuple of (bibtex_string, {url: citekey}) where citekey
        is a sanitized identifier like "result_1", "result_2", etc.
        Returns ("", {}) for empty input.
    """
    if not search_results:
        logger.info("No search results for topic; skipping bibliography generation")
        return "", {}

    entries: list[str] = []
    url_to_citekey: dict[str, str] = {}

    for idx, result in enumerate(search_results, start=1):
        citekey = f"result_{idx}"
        url_to_citekey[result.url] = citekey

        year = str(result.discovered_date.year)

        # Build the BibTeX entry
        entry = (
            f"@misc{{{citekey},\n"
            f"    title = {{{result.title}}},\n"
            f"    url = {{{result.url}}},\n"
            f"    note = {{{result.snippet}}},\n"
            f"    year = {{{year}}}\n"
            f"}}"
        )
        entries.append(entry)

    bibtex_string = "\n\n".join(entries) + "\n"
    return bibtex_string, url_to_citekey


def insert_citations(
    latex_body: str,
    search_results: list[WebSearchResult],
    url_to_citekey: dict[str, str],
) -> str:
    r"""Insert \cite{} commands into LaTeX body where URLs appear.

    For each URL in the url_to_citekey mapping that appears in the
    latex_body text, a ``\cite{citekey}`` command is appended after
    the URL occurrence.

    Args:
        latex_body: LaTeX body text.
        search_results: The search results to match against.
        url_to_citekey: Mapping from URL to BibTeX cite key.

    Returns:
        LaTeX body with \cite{} commands inserted after matched URLs.
    """
    if not url_to_citekey:
        return latex_body

    result = latex_body
    for url, citekey in url_to_citekey.items():
        # Replace each occurrence of the URL with the URL followed by \cite{citekey}
        cite_command = f"\\cite{{{citekey}}}"
        # Only insert citation if not already present immediately after the URL
        pattern = re.escape(url) + r"(?!" + re.escape(cite_command) + r")"
        # re.sub replacement strings need backslashes escaped
        replacement = (url + cite_command).replace("\\", "\\\\")
        result = re.sub(pattern, replacement, result)

    return result


# Standard plan section order (matches pdf_exporter.py)
PLAN_SECTION_ORDER = [
    "Executive Summary",
    "Company Description",
    "Market Analysis",
    "Organization & Management",
    "Service or Product Line",
    "Marketing & Sales",
    "Funding Request",
    "Financial Projections",
]
APPENDIX_SECTION = "Appendix"


def _build_preamble(
    title: str, has_bibliography: bool = False, bib_filename: str = ""
) -> str:
    r"""Build the LaTeX document preamble.

    Includes: \documentclass{article}, inputenc, fontenc, geometry,
    hyperref, and optionally biblatex with \addbibresource.

    Args:
        title: Document title for the \title{} command.
        has_bibliography: Whether to include biblatex package and resource.
        bib_filename: The .bib filename (without path) for \addbibresource.

    Returns:
        LaTeX preamble string ending with \begin{document} and \maketitle.
    """
    lines = [
        r"\documentclass{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{geometry}",
        r"\usepackage{hyperref}",
    ]

    if has_bibliography and bib_filename:
        lines.append(r"\usepackage[backend=biber]{biblatex}")
        lines.append(rf"\addbibresource{{{bib_filename}}}")

    lines.append("")
    lines.append(rf"\title{{{_escape_latex_special_chars(title)}}}")
    lines.append(r"\date{\today}")
    lines.append("")
    lines.append(r"\begin{document}")
    lines.append(r"\maketitle")
    lines.append("")

    return "\n".join(lines)


def _sort_plan_sections(sections: list[PlanSection]) -> list[PlanSection]:
    """Sort plan sections in standard order with Appendix last.

    Sections not in the standard order are placed after standard sections
    but before Appendix.

    Args:
        sections: Unsorted list of PlanSection objects.

    Returns:
        Sorted list of PlanSection objects.
    """
    ordered: list[tuple[int, PlanSection]] = []
    appendix: PlanSection | None = None

    for section in sections:
        if section.section_name == APPENDIX_SECTION:
            appendix = section
        else:
            try:
                idx = PLAN_SECTION_ORDER.index(section.section_name)
                ordered.append((idx, section))
            except ValueError:
                # Section not in standard list — place after standard sections
                ordered.append((999, section))

    ordered.sort(key=lambda x: x[0])
    result = [s for _, s in ordered]

    if appendix:
        result.append(appendix)

    return result


def export_canvas_latex(
    topic_name: str,
    canvas_elements: list[CanvasElement],
    output_dir: Path,
) -> Path:
    """Export Business Model Canvas to a .tex file.

    Generates a LaTeX document with each canvas element as a section,
    with the element content converted from markdown to LaTeX.

    Args:
        topic_name: Name of the topic (used for title and filename).
        canvas_elements: List of canvas elements to export.
        output_dir: Directory where the .tex file will be written.

    Returns:
        Path to the generated .tex file, or Path("") if no content.
    """
    if not canvas_elements:
        logger.warning("No canvas elements to export for topic %s", topic_name)
        return Path("")

    preamble = _build_preamble(f"{topic_name} — Business Model Canvas")

    body_lines: list[str] = []
    for element in canvas_elements:
        body_lines.append(
            r"\section{" + _escape_latex_special_chars(element.element_name) + "}"
        )
        body_lines.append("")
        body_lines.append(markdown_to_latex(element.content, heading_offset=1))
        body_lines.append("")

    document = preamble + "\n".join(body_lines) + "\n" + r"\end{document}" + "\n"

    filename = f"{topic_name.replace(' ', '_')}_Canvas.tex"
    out_path = output_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")

    logger.info("Exported canvas LaTeX: %s", out_path)
    return out_path


def export_voices_latex(
    topic_name: str,
    voices: list[VoicePersona],
    output_dir: Path,
) -> Path:
    """Export Voice Personas to a .tex file.

    Generates a LaTeX document with each persona as a section containing
    their name, description, and communication style.

    Args:
        topic_name: Name of the topic (used for title and filename).
        voices: List of voice personas to export.
        output_dir: Directory where the .tex file will be written.

    Returns:
        Path to the generated .tex file, or Path("") if no content.
    """
    if not voices:
        logger.warning("No voices to export for topic %s", topic_name)
        return Path("")

    preamble = _build_preamble(f"{topic_name} — Voice Personas")

    body_lines: list[str] = []
    for persona in voices:
        body_lines.append(
            r"\section{" + _escape_latex_special_chars(persona.name) + "}"
        )
        body_lines.append("")
        body_lines.append(r"\subsection{Description}")
        body_lines.append(markdown_to_latex(persona.description, heading_offset=2))
        body_lines.append("")
        body_lines.append(r"\subsection{Communication Style}")
        body_lines.append(markdown_to_latex(persona.communication_style, heading_offset=2))
        body_lines.append("")

    document = preamble + "\n".join(body_lines) + "\n" + r"\end{document}" + "\n"

    filename = f"{topic_name.replace(' ', '_')}_Voices.tex"
    out_path = output_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")

    logger.info("Exported voices LaTeX: %s", out_path)
    return out_path


def export_plan_latex(
    topic_name: str,
    plan_sections: list[PlanSection],
    output_dir: Path,
    search_results: list[WebSearchResult] | None = None,
) -> Path:
    """Export Business Plan to a .tex file with optional bibliography.

    Generates a LaTeX document with plan sections in standard order.
    If search_results are provided, generates a companion .bib file
    and inserts \\cite{} references in the document body.

    Args:
        topic_name: Name of the topic (used for title and filename).
        plan_sections: List of plan sections to export.
        output_dir: Directory where the .tex file will be written.
        search_results: Optional web search results for bibliography.

    Returns:
        Path to the generated .tex file, or Path("") if no content.
    """
    if not plan_sections:
        logger.warning("No plan sections to export for topic %s", topic_name)
        return Path("")

    # Determine bibliography needs
    has_bibliography = bool(search_results)
    bib_filename = ""
    url_to_citekey: dict[str, str] = {}
    bibtex_string = ""

    if has_bibliography:
        bibtex_string, url_to_citekey = generate_bibtex(search_results)  # type: ignore[arg-type]
        bib_filename = f"{topic_name.replace(' ', '_')}_BusinessPlan.bib"
        # If generate_bibtex returned empty (shouldn't happen with non-empty list),
        # treat as no bibliography
        if not bibtex_string:
            has_bibliography = False
            bib_filename = ""

    preamble = _build_preamble(
        f"{topic_name} — Business Plan",
        has_bibliography=has_bibliography,
        bib_filename=bib_filename,
    )

    # Sort sections in standard order
    sorted_sections = _sort_plan_sections(plan_sections)

    body_lines: list[str] = []
    for section in sorted_sections:
        body_lines.append(
            r"\section{" + _escape_latex_special_chars(section.section_name) + "}"
        )
        body_lines.append("")
        latex_content = markdown_to_latex(section.content, heading_offset=1)
        # Insert citations if we have a bibliography
        if has_bibliography and url_to_citekey:
            latex_content = insert_citations(
                latex_content, search_results or [], url_to_citekey
            )
        body_lines.append(latex_content)
        body_lines.append("")

    # Add bibliography printing at the end if applicable
    if has_bibliography:
        body_lines.append(r"\printbibliography")
        body_lines.append("")

    document = preamble + "\n".join(body_lines) + "\n" + r"\end{document}" + "\n"

    filename = f"{topic_name.replace(' ', '_')}_BusinessPlan.tex"
    out_path = output_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document, encoding="utf-8")

    # Write companion .bib file if bibliography exists
    if has_bibliography and bibtex_string:
        bib_path = output_dir / bib_filename
        bib_path.write_text(bibtex_string, encoding="utf-8")
        logger.info("Exported bibliography: %s", bib_path)

    logger.info("Exported plan LaTeX: %s", out_path)
    return out_path
