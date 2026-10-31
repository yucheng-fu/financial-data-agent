from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document_chunk import RetrievedChunk
from financial_data_agent.db.repositories.document_chunk import DocumentChunkRepository
from financial_data_agent.ingestion.embeddings import Embedder


def retrieve_chunks(
    session: Session,
    embedder: Embedder,
    query: str,
    tickers: Sequence[str],
    years: Sequence[int],
    quarters: Sequence[int],
    limit: int,
) -> list[RetrievedChunk]:
    """Return the chunks most similar to a query, within the given filings.

    Args:
        session: Database session used for the search.
        embedder: Embedding backend; must be the one the corpus was embedded with.
        query: Natural-language query.
        tickers: Tickers to restrict to, or empty for all.
        years: Reporting years to restrict to, or empty for all.
        quarters: Reporting quarters to restrict to, or empty for all. A quarter restricts to quarterly filings.
        limit: Maximum number of chunks to return.

    Returns:
        The closest chunks first.
    """
    embedding = embedder.embed_query(query)
    return DocumentChunkRepository(session).search_similar(embedding, tickers, years, quarters, limit)
