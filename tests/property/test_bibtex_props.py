"""Property-based tests for BibTeX generation and citation insertion.

Tests the generate_bibtex() function for entry completeness and the
insert_citations() function for correct citation command insertion.

Validates: Requirements 3.1, 3.3
"""

import re
from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.db.models import WebSearchResult
from business_coach.export.latex_exporter import generate_bibtex, insert_citations

# ---------------------------------------------------------------------------
# Strategies — generators for WebSearchResult and related data
# ---------------------------------------------------------------------------

# Safe alphabet for titles and snippets (avoids BibTeX special chars like {, })
_SAFE_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "

_safe_text = st.text(
    alphabet=_SAFE_ALPHABET,
    min_size=1,
    max_size=50,
).map(lambda s: s.strip()).filter(lambda s: len(s) > 0)

# URL strategy: generate plausible URLs with unique paths
_url_strategy = st.builds(
    lambda domain, path: f"https://{domain}.example.com/{path}",
    domain=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz",
        min_size=3,
        max_size=10,
    ),
    path=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=5,
        max_size=20,
    ),
)

# Datetime strategy for discovered_date
_datetime_strategy = st.builds(
    lambda year, month, day: datetime(year, month, day, tzinfo=timezone.utc),
    year=st.integers(min_value=2000, max_value=2025),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
)

# WebSearchResult strategy
_web_search_result_strategy = st.builds(
    lambda url, title, snippet, discovered_date: WebSearchResult(
        url=url,
        title=title,
        snippet=snippet,
        discovered_date=discovered_date,
    ),
    url=_url_strategy,
    title=_safe_text,
    snippet=_safe_text,
    discovered_date=_datetime_strategy,
)

# List of WebSearchResult with unique URLs
_search_results_list = st.lists(
    _web_search_result_strategy,
    min_size=1,
    max_size=10,
    unique_by=lambda r: r.url,
)


# ---------------------------------------------------------------------------
# Property 4: BibTeX entry completeness
# Feature: bc-improvements, Property 4: BibTeX entry completeness
# ---------------------------------------------------------------------------


class TestBibtexEntryCompleteness:
    """Property 4: BibTeX entry completeness.

    For any non-empty list of WebSearchResult objects, generate_bibtex() SHALL
    produce a BibTeX string containing exactly one @misc entry per search result,
    and each entry SHALL contain the fields title, url, note, and year with values
    matching the corresponding WebSearchResult attributes.

    **Validates: Requirements 3.1**
    """

    @given(results=_search_results_list)
    @settings(max_examples=100)
    def test_one_misc_entry_per_result(self, results: list[WebSearchResult]) -> None:
        """Number of @misc entries equals number of search results."""
        bibtex_string, url_to_citekey = generate_bibtex(results)

        misc_count = bibtex_string.count("@misc{")
        assert misc_count == len(results), (
            f"Expected {len(results)} @misc entries, got {misc_count}.\n"
            f"BibTeX output:\n{bibtex_string}"
        )

    @given(results=_search_results_list)
    @settings(max_examples=100)
    def test_each_entry_contains_required_fields(
        self, results: list[WebSearchResult]
    ) -> None:
        """Each @misc entry contains title, url, note, and year fields."""
        bibtex_string, url_to_citekey = generate_bibtex(results)

        # Split into individual entries using the @misc{ delimiter
        # Each entry ends with a closing } on its own line
        entries = re.split(r"@misc\{", bibtex_string)
        # First element is empty (before the first @misc{)
        entries = [e for e in entries if e.strip()]

        assert len(entries) == len(results), (
            f"Expected {len(results)} parsed entries, got {len(entries)}."
        )

        for i, entry in enumerate(entries):
            required_fields = ["title", "url", "note", "year"]
            for field in required_fields:
                assert f"{field} = " in entry, (
                    f"Entry {i + 1} missing field '{field}'.\n"
                    f"Entry content:\n{entry}"
                )

    @given(results=_search_results_list)
    @settings(max_examples=100)
    def test_entry_values_match_search_results(
        self, results: list[WebSearchResult]
    ) -> None:
        """Field values in BibTeX entries match WebSearchResult attributes."""
        bibtex_string, url_to_citekey = generate_bibtex(results)

        for idx, result in enumerate(results):
            citekey = f"result_{idx + 1}"

            # Verify citekey is in the mapping
            assert result.url in url_to_citekey, (
                f"URL '{result.url}' not found in url_to_citekey mapping."
            )
            assert url_to_citekey[result.url] == citekey, (
                f"Expected citekey '{citekey}' for URL '{result.url}', "
                f"got '{url_to_citekey[result.url]}'."
            )

            # Verify field values in the BibTeX string
            assert f"title = {{{result.title}}}" in bibtex_string, (
                f"Title '{result.title}' not found in BibTeX entry for {citekey}."
            )
            assert f"url = {{{result.url}}}" in bibtex_string, (
                f"URL '{result.url}' not found in BibTeX entry for {citekey}."
            )
            assert f"note = {{{result.snippet}}}" in bibtex_string, (
                f"Snippet '{result.snippet}' not found in BibTeX entry for {citekey}."
            )
            expected_year = str(result.discovered_date.year)
            assert f"year = {{{expected_year}}}" in bibtex_string, (
                f"Year '{expected_year}' not found in BibTeX entry for {citekey}."
            )

    @given(results=_search_results_list)
    @settings(max_examples=100)
    def test_url_to_citekey_mapping_complete(
        self, results: list[WebSearchResult]
    ) -> None:
        """The url_to_citekey mapping has one entry per search result."""
        _bibtex_string, url_to_citekey = generate_bibtex(results)

        assert len(url_to_citekey) == len(results), (
            f"Expected {len(results)} entries in url_to_citekey, "
            f"got {len(url_to_citekey)}."
        )

        for result in results:
            assert result.url in url_to_citekey, (
                f"URL '{result.url}' missing from url_to_citekey mapping."
            )


# ---------------------------------------------------------------------------
# Property 5: Citation insertion correctness
# Feature: bc-improvements, Property 5: Citation insertion correctness
# ---------------------------------------------------------------------------

# Strategy: generate a url_to_citekey mapping with unique URLs and citekeys
_citekey_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=3,
    max_size=15,
).filter(lambda s: len(s) > 0 and s[0].isalpha())

_url_citekey_pair = st.tuples(_url_strategy, _citekey_strategy)

_url_to_citekey_mapping = st.lists(
    _url_citekey_pair,
    min_size=1,
    max_size=5,
    unique_by=lambda pair: pair[0],
).map(dict)


def _build_latex_body_with_urls(
    url_to_citekey: dict[str, str], included_urls: list[str]
) -> str:
    """Build a LaTeX body text that contains the specified URLs."""
    body_parts = []
    for url in included_urls:
        body_parts.append(f"See the source at {url} for more details.")
    # Add some filler text
    body_parts.append("This is additional content without URLs.")
    return "\n".join(body_parts)


class TestCitationInsertionCorrectness:
    """Property 5: Citation insertion correctness.

    For any LaTeX body text that contains URLs matching entries in a
    url_to_citekey mapping, insert_citations() SHALL insert a \\cite{citekey}
    command adjacent to each matched URL, and the total number of \\cite{}
    commands in the output SHALL equal the number of matched URLs in the input.

    **Validates: Requirements 3.3**
    """

    @given(
        url_to_citekey=_url_to_citekey_mapping,
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_cite_count_equals_matched_url_count(
        self, url_to_citekey: dict[str, str], data: st.DataObject
    ) -> None:
        """Number of \\cite{} commands equals number of matched URLs."""
        urls = list(url_to_citekey.keys())

        # Choose a subset of URLs to include in the body (at least 1)
        included_urls = data.draw(
            st.lists(
                st.sampled_from(urls),
                min_size=1,
                max_size=len(urls),
                unique=True,
            )
        )

        # Build LaTeX body containing those URLs (each URL appears exactly once)
        latex_body = _build_latex_body_with_urls(url_to_citekey, included_urls)

        # Create corresponding WebSearchResult objects
        search_results = [
            WebSearchResult(
                url=url,
                title="Test Title",
                snippet="Test snippet",
            )
            for url in urls
        ]

        # Insert citations
        result = insert_citations(latex_body, search_results, url_to_citekey)

        # Count \cite{...} commands in output
        cite_pattern = r"\\cite\{[^}]+\}"
        cite_matches = re.findall(cite_pattern, result)

        expected_count = len(included_urls)
        assert len(cite_matches) == expected_count, (
            f"Expected {expected_count} \\cite{{}} commands, "
            f"got {len(cite_matches)}.\n"
            f"Included URLs: {included_urls}\n"
            f"Result:\n{result}"
        )

    @given(
        url_to_citekey=_url_to_citekey_mapping,
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_correct_citekeys_inserted(
        self, url_to_citekey: dict[str, str], data: st.DataObject
    ) -> None:
        """Each inserted \\cite{} uses the correct citekey for its URL."""
        urls = list(url_to_citekey.keys())

        # Choose a subset of URLs to include
        included_urls = data.draw(
            st.lists(
                st.sampled_from(urls),
                min_size=1,
                max_size=len(urls),
                unique=True,
            )
        )

        latex_body = _build_latex_body_with_urls(url_to_citekey, included_urls)

        search_results = [
            WebSearchResult(
                url=url,
                title="Test Title",
                snippet="Test snippet",
            )
            for url in urls
        ]

        result = insert_citations(latex_body, search_results, url_to_citekey)

        # Verify each included URL has its correct \cite{citekey} adjacent
        for url in included_urls:
            expected_citekey = url_to_citekey[url]
            cite_command = f"\\cite{{{expected_citekey}}}"
            assert cite_command in result, (
                f"Expected '{cite_command}' in output for URL '{url}'.\n"
                f"Result:\n{result}"
            )
