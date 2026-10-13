from __future__ import annotations

from sqlalchemy.orm import Session

from financial_data_agent.agent.tablerag.constants import RETRIEVE_TOP_K
from financial_data_agent.agent.tablerag.state import TableRAGState, current_subquery
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk
from financial_data_agent.ingestion.embeddings import Embedder
from financial_data_agent.services.chunk_retrieval import retrieve_chunks


def retrieve(state: TableRAGState, session: Session, embedder: Embedder) -> dict[str, list[RetrievedChunk]]:
    """Retrieve the chunks closest to the subquery, within the filings it names.

    Args:
        state: The subgraph state.
        session: Database session used for the search.
        embedder: Embedding backend.

    Returns:
        The candidate chunks, closest first.
    """
    current = current_subquery(state)
    candidates = retrieve_chunks(
        session, embedder, current.subquery, current.tickers, current.years, current.quarters, RETRIEVE_TOP_K
    )
    return {"candidates": candidates}
