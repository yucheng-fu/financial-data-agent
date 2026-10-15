from __future__ import annotations

from financial_data_agent.agent.tablerag.constants import RERANK_TOP_K
from financial_data_agent.agent.tablerag.rerank import rerank
from financial_data_agent.agent.tablerag.state import TableRAGState, current_subquery
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk


def rerank_candidates(state: TableRAGState) -> dict[str, list[RetrievedChunk]]:
    """Keep the best candidate chunks by fusing vector and keyword rankings.

    Args:
        state: The subgraph state.

    Returns:
        The reranked chunks, best first.
    """
    return {"reranked": rerank(current_subquery(state).subquery, state["candidates"], RERANK_TOP_K)}
