from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from financial_data_agent.constants import (
    CHARS_PER_TOKEN,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    HEADER_KEYS,
    HEADERS_TO_SPLIT_ON,
    HEADING_SEPARATOR,
    TABLE_DIVIDER_PATTERN,
    TABLE_ROW_PATTERN,
)


@dataclass(frozen=True, slots=True)
class MarkdownChunk:
    """A span of a filing ready for embedding."""

    index: int
    content: str
    is_table: bool
    heading_path: str | None
    token_count: int


def estimate_tokens(text: str) -> int:
    """Estimate how many tokens a string occupies.

    A character heuristic rather than a real tokenizer, so the result is approximate.

    Args:
        text: Text to measure.

    Returns:
        The estimated token count.
    """
    return len(text) // CHARS_PER_TOKEN


def build_heading_path(metadata: dict[str, str]) -> str | None:
    """Join the heading metadata of a section into a single path.

    Args:
        metadata: Header metadata produced by MarkdownHeaderTextSplitter.

    Returns:
        The joined heading path, or None when the section sits under no heading.
    """
    headings = [metadata[key] for key in HEADER_KEYS if key in metadata]
    return HEADING_SEPARATOR.join(headings) if headings else None


def measure_table(lines: Sequence[str], index: int) -> int:
    """Measure the markdown table starting at a line.

    A table is a row line followed by a divider line, then every consecutive row line.

    Args:
        lines: Lines of the section.
        index: Index of the candidate first line.

    Returns:
        The number of lines the table occupies, or 0 if no table starts here.
    """
    if index + 1 >= len(lines):
        return 0
    if TABLE_ROW_PATTERN.match(lines[index]) is None:
        return 0
    if TABLE_DIVIDER_PATTERN.match(lines[index + 1]) is None:
        return 0
    length = 2
    while index + length < len(lines) and TABLE_ROW_PATTERN.match(lines[index + length]) is not None:
        length += 1
    return length


def split_table_segments(text: str) -> list[tuple[str, bool]]:
    """Separate whole markdown tables from the prose around them.

    Args:
        text: Text of one heading section.

    Returns:
        Segments in document order, each flagged as a table or as prose.
    """
    lines = text.splitlines()
    segments: list[tuple[str, bool]] = []
    buffer: list[str] = []
    index = 0

    while index < len(lines):
        table_length = measure_table(lines, index)
        if table_length == 0:
            buffer.append(lines[index])
            index += 1
            continue
        if buffer:
            segments.append(("\n".join(buffer).strip(), False))
            buffer = []
        segments.append(("\n".join(lines[index : index + table_length]).strip(), True))
        index += table_length

    if buffer:
        segments.append(("\n".join(buffer).strip(), False))

    return [(segment, is_table) for segment, is_table in segments if segment]


def chunk_markdown(
    markdown: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[MarkdownChunk]:
    """Split a markdown filing into chunks ready for embedding.

    Sections are cut on headings first, so every chunk carries the heading path it sits
    under. A table always becomes its own chunk, even when it exceeds the bound, and is
    never handed to the recursive splitter. Prose is split within its section, with
    overlap carried between consecutive pieces.

    Args:
        markdown: Markdown source of the filing.
        max_tokens: Soft upper bound on the tokens in a prose chunk.
        overlap_tokens: Token budget repeated between consecutive prose chunks.

    Returns:
        The chunks in document order.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    prose_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens * CHARS_PER_TOKEN,
        chunk_overlap=overlap_tokens * CHARS_PER_TOKEN,
    )

    chunks: list[MarkdownChunk] = []
    for section in header_splitter.split_text(markdown):
        heading_path = build_heading_path(section.metadata)
        for segment, is_table in split_table_segments(section.page_content):
            contents = [segment] if is_table else prose_splitter.split_text(segment)
            for content in contents:
                chunks.append(
                    MarkdownChunk(
                        index=len(chunks),
                        content=content,
                        is_table=is_table,
                        heading_path=heading_path,
                        token_count=estimate_tokens(content),
                    )
                )
    return chunks
