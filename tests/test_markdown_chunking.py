from __future__ import annotations

from financial_data_agent.ingestion.markdown_chunking import (
    build_heading_path,
    chunk_markdown,
    estimate_tokens,
    measure_table,
    split_table_segments,
)

TABLE = """| Item | 2026 | 2025 |
|---:|:---|---|
| Revenue | 90,753 | 81,797 |
| Net income | 23,636 | 19,442 |
"""

FILING = f"""# Apple Inc.

## Item 1. Financial Statements

Condensed consolidated statements follow.

### Condensed Consolidated Statements of Operations

{TABLE}
## Item 2. MD&A

Revenue increased year over year.
"""


def test_measure_table_spans_the_whole_table() -> None:
    lines = TABLE.splitlines()

    assert measure_table(lines, 0) == 4


def test_measure_table_rejects_a_row_without_a_divider() -> None:
    lines = "| Revenue | 90,753 |\n| Net income | 23,636 |".splitlines()

    assert measure_table(lines, 0) == 0


def test_split_table_segments_separates_a_table_from_the_prose_around_it() -> None:
    section = f"Intro sentence.\n\n{TABLE}\nClosing sentence."

    segments = split_table_segments(section)

    assert [is_table for _, is_table in segments] == [False, True, False]
    assert segments[0][0] == "Intro sentence."
    assert segments[1][0] == TABLE.strip()
    assert segments[2][0] == "Closing sentence."


def test_build_heading_path_joins_the_levels_present() -> None:
    assert build_heading_path({"h1": "Apple Inc.", "h2": "Item 2. MD&A"}) == "Apple Inc. > Item 2. MD&A"
    assert build_heading_path({}) is None


def test_heading_path_tracks_a_descent_and_pops_back_up() -> None:
    chunks = chunk_markdown(FILING)
    paths = {chunk.content.splitlines()[-1].strip(): chunk.heading_path for chunk in chunks}

    assert paths["Condensed consolidated statements follow."] == "Apple Inc. > Item 1. Financial Statements"
    assert paths["Revenue increased year over year."] == "Apple Inc. > Item 2. MD&A"

    table_chunk = next(chunk for chunk in chunks if chunk.is_table)
    assert table_chunk.heading_path == (
        "Apple Inc. > Item 1. Financial Statements > Condensed Consolidated Statements of Operations"
    )


def test_a_table_becomes_its_own_chunk() -> None:
    chunks = chunk_markdown(FILING)

    table_chunks = [chunk for chunk in chunks if chunk.is_table]
    assert len(table_chunks) == 1
    assert table_chunks[0].content == TABLE.strip()


def test_an_oversized_table_is_never_split() -> None:
    rows = "\n".join(f"| Row {number} | {number * 1000} | {number * 2000} |" for number in range(400))
    markdown = f"## Balance Sheet\n\n| Item | 2026 | 2025 |\n|---|---|---|\n{rows}\n"

    chunks = chunk_markdown(markdown, max_tokens=100, overlap_tokens=20)

    table_chunks = [chunk for chunk in chunks if chunk.is_table]
    assert len(table_chunks) == 1
    assert table_chunks[0].token_count > 100
    assert table_chunks[0].content.count("| Row ") == 400


def test_prose_is_split_within_its_section_and_tables_stay_clean() -> None:
    paragraphs = "\n\n".join(f"Paragraph {number} about operating results." for number in range(12))
    markdown = f"## Item 2. MD&A\n\n{paragraphs}\n\n{TABLE}"

    chunks = chunk_markdown(markdown, max_tokens=40, overlap_tokens=10)
    prose_chunks = [chunk for chunk in chunks if not chunk.is_table]

    assert len(prose_chunks) > 1
    assert all(chunk.heading_path == "Item 2. MD&A" for chunk in chunks)

    table_chunk = next(chunk for chunk in chunks if chunk.is_table)
    assert table_chunk.content == TABLE.strip()
    assert "Paragraph" not in table_chunk.content


def test_chunks_are_indexed_consecutively_from_zero() -> None:
    chunks = chunk_markdown(FILING, max_tokens=20, overlap_tokens=5)

    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))


def test_chunking_empty_markdown_returns_no_chunks() -> None:
    assert chunk_markdown("") == []


def test_estimate_tokens_uses_the_character_heuristic() -> None:
    assert estimate_tokens("a" * 400) == 100
