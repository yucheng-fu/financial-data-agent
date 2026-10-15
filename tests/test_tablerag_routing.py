from __future__ import annotations

from langgraph.graph import END

from financial_data_agent.agent.tablerag.parsing import SubQueryAction
from financial_data_agent.agent.tablerag.routing import mentions_metric, route_after_decompose, route_sql
from financial_data_agent.agent.tablerag.state import TableRAGState, initial_state
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk

SQL = "SELECT revenue FROM financial_metrics"


def make_chunk(is_table: bool) -> RetrievedChunk:
    return RetrievedChunk(
        content="| Revenue | 94,930 |" if is_table else "Apple designs smartphones.",
        is_table=is_table,
        heading_path=None,
        chunk_index=0,
        ticker="AAPL",
        year=2024,
        quarter=3,
        accession_number="0000320193-24-000081",
    )


def make_state(subquery: str, sql: str | None, reranked: list[RetrievedChunk]) -> TableRAGState:
    state = initial_state("question", max_iterations=2)
    state["current"] = SubQueryAction(action="subquery", subquery=subquery, sql=sql)
    state["reranked"] = reranked
    return state


def test_mentions_metric_matches_metric_names_case_insensitively() -> None:
    assert mentions_metric("What was Apple's Free Cash Flow?")
    assert not mentions_metric("Who is Apple's CEO?")


def test_route_sql_runs_sql_when_a_table_chunk_was_retrieved() -> None:
    assert route_sql(make_state("Who is the CEO?", SQL, [make_chunk(is_table=True)])) == "sql"


def test_route_sql_runs_sql_when_subquery_names_a_metric() -> None:
    assert route_sql(make_state("What was net income?", SQL, [make_chunk(is_table=False)])) == "sql"


def test_route_sql_skips_sql_without_table_chunk_or_metric() -> None:
    assert route_sql(make_state("Who is the CEO?", SQL, [make_chunk(is_table=False)])) == "intermediate_answer"


def test_route_sql_skips_sql_when_model_wrote_none() -> None:
    assert route_sql(make_state("What was revenue?", None, [make_chunk(is_table=True)])) == "intermediate_answer"


def test_route_after_decompose_ends_once_answered() -> None:
    state = initial_state("question", max_iterations=2)
    state["answer"] = "42"

    assert route_after_decompose(state) == END


def test_route_after_decompose_ends_past_iteration_limit() -> None:
    state = initial_state("question", max_iterations=2)
    state["iteration"] = 3

    assert route_after_decompose(state) == END


def test_route_after_decompose_retrieves_within_iteration_limit() -> None:
    state = initial_state("question", max_iterations=2)
    state["iteration"] = 2

    assert route_after_decompose(state) == "retrieve"
