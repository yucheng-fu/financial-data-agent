from __future__ import annotations

from financial_data_agent.agent.tablerag.rerank import bm25_scores, reciprocal_rank_fusion, rerank
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk


def make_chunk(content: str, is_table: bool = False) -> RetrievedChunk:
    return RetrievedChunk(
        content=content,
        is_table=is_table,
        heading_path=None,
        chunk_index=0,
        ticker="AAPL",
        year=2024,
        quarter=3,
        accession_number="0000320193-24-000081",
    )


def test_bm25_scores_rank_documents_containing_query_terms_higher() -> None:
    scores = bm25_scores("operating income", ["net sales grew", "operating income was 30 billion", "income taxes"])

    assert scores[1] > scores[2] > scores[0] == 0.0


def test_reciprocal_rank_fusion_breaks_ties_by_first_ranking() -> None:
    assert reciprocal_rank_fusion([[0, 1], [1, 0]]) == [0, 1]


def test_rerank_lifts_keyword_match_above_closer_chunk_without_overlap() -> None:
    closest = make_chunk("Risk factors include competition.")
    second = make_chunk("The company leases office space.")
    keyword = make_chunk("Operating income was 30 billion dollars.", is_table=True)

    assert rerank("operating income", [closest, second, keyword], top_k=2) == [closest, keyword]


def test_rerank_handles_no_chunks() -> None:
    assert rerank("operating income", [], top_k=3) == []
