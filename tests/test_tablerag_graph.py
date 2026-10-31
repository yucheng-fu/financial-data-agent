from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from itertools import cycle
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.agent.tablerag.graph import build_tablerag_graph, recursion_limit_for
from financial_data_agent.agent.tablerag.nodes import retrieve as retrieve_node
from financial_data_agent.agent.tablerag.nodes.decompose import decompose
from financial_data_agent.agent.tablerag.nodes.sql import run_sql
from financial_data_agent.agent.tablerag.parsing import SubQueryAction
from financial_data_agent.agent.tablerag.state import Citation, MissingFiling, initial_state, union
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.ingestion.embeddings import Embedder
from financial_data_agent.services.sql_query import SQLQueryResult

ACCESSION_NUMBER = "0000320193-24-000081"
TABLE_CHUNK = RetrievedChunk(
    content="| Revenue | 94,930 |",
    is_table=True,
    heading_path="Item 1. Financial Statements",
    chunk_index=4,
    ticker="AAPL",
    reporting_year=2024,
    reporting_quarter=3,
    period_type="quarterly",
    accession_number=ACCESSION_NUMBER,
)
TEXT_CHUNK = RetrievedChunk(
    content="Tim Cook is the Chief Executive Officer.",
    is_table=False,
    heading_path="Item 5. Other Information",
    chunk_index=9,
    ticker="AAPL",
    reporting_year=2024,
    reporting_quarter=3,
    period_type="quarterly",
    accession_number=ACCESSION_NUMBER,
)


def make_reader_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    CompanyRepository(session).create(CompanyDTO(ticker="AAPL", name="Apple Inc.", cik="0000320193"))
    return session


def subquery_message(subquery: str, ticker: str = "AAPL", sql: str | None = None) -> AIMessage:
    action = {"action": "subquery", "subquery": subquery, "tickers": [ticker], "years": [2024], "quarters": [3]}
    return AIMessage(content=json.dumps({**action, "sql": sql}))


def answer_message(answer: str) -> AIMessage:
    return AIMessage(content=json.dumps({"action": "answer", "answer": answer}))


def stub_retrieval(monkeypatch: pytest.MonkeyPatch, chunks: Sequence[RetrievedChunk]) -> None:
    monkeypatch.setattr(retrieve_node, "retrieve_chunks", lambda *args, **kwargs: list(chunks))


def run_graph(messages: Iterable[AIMessage], max_iterations: int = 2) -> tuple[list[str], dict[str, Any]]:
    graph = build_tablerag_graph(
        session=MagicMock(spec=Session),
        reader_session=make_reader_session(),
        chat_model=GenericFakeChatModel(messages=iter(messages)),
        embedder=MagicMock(spec=Embedder),
    )
    visited: list[str] = []
    final: dict[str, Any] = {}
    for mode, chunk in graph.stream(
        initial_state("What was Apple's revenue in Q3 2024?", max_iterations),
        config={"recursion_limit": recursion_limit_for(max_iterations)},
        stream_mode=["updates", "values"],
    ):
        if mode == "updates":
            visited.extend(chunk)
        else:
            final = chunk
    return visited, final


def test_tablerag_graph_visits_sql_when_table_chunk_retrieved(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_retrieval(monkeypatch, [TABLE_CHUNK])

    visited, final = run_graph(
        [
            subquery_message("What was Apple's revenue in Q3 2024?", sql="SELECT ticker FROM companies"),
            AIMessage(content="Revenue was 94,930 million USD."),
            answer_message("Apple's revenue in Q3 2024 was 94,930 million USD."),
        ]
    )

    assert visited == ["decompose", "retrieve", "rerank", "sql", "intermediate_answer", "decompose"]
    assert final["answer"] == "Apple's revenue in Q3 2024 was 94,930 million USD."
    assert final["sql_result"] == SQLQueryResult(columns=["ticker"], rows=[("AAPL",)], truncated=False)
    assert final["citations"] == [
        Citation("AAPL", 2024, 3, "quarterly", ACCESSION_NUMBER, 4, "Item 1. Financial Statements")
    ]
    assert final["missing"] == []


def test_tablerag_graph_skips_sql_without_table_chunk_or_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_retrieval(monkeypatch, [TEXT_CHUNK])

    visited, final = run_graph(
        [
            subquery_message("Who is Apple's chief executive officer?", sql="SELECT ticker FROM companies"),
            AIMessage(content="Tim Cook."),
            answer_message("Tim Cook."),
        ]
    )

    assert visited == ["decompose", "retrieve", "rerank", "intermediate_answer", "decompose"]
    assert final["sql_result"] is None
    assert final["answer"] == "Tim Cook."


def test_tablerag_graph_reports_missing_filing_when_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_retrieval(monkeypatch, [])
    sql = "SELECT ticker FROM companies WHERE ticker = 'MSFT'"

    visited, final = run_graph(
        [
            subquery_message("What was Microsoft's revenue in Q3 2024?", ticker="MSFT", sql=sql),
            AIMessage(content="No data for Microsoft."),
            answer_message("The Microsoft filing for Q3 2024 is not stored."),
        ]
    )

    assert "sql" in visited
    assert final["missing"] == [MissingFiling("MSFT", 2024, 3)]
    assert final["citations"] == []


def test_tablerag_graph_ends_without_answer_at_max_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_retrieval(monkeypatch, [TEXT_CHUNK])

    visited, final = run_graph(cycle([subquery_message("Who is the CEO?"), AIMessage(content="Unclear.")]))

    assert visited.count("decompose") == 3
    assert len(final["history"]) == 2
    assert final["answer"] is None


def test_decompose_clears_previous_sql_result() -> None:
    state = initial_state("What was Apple's revenue?")
    state["sql_result"] = SQLQueryResult(columns=["ticker"], rows=[("AAPL",)], truncated=False)
    state["sql_error"] = "previous error"
    model = GenericFakeChatModel(messages=iter([subquery_message("What was Apple's revenue?")]))

    update = decompose(state, model)

    assert update["sql_result"] is None
    assert update["sql_error"] is None
    assert update["iteration"] == 1


def test_run_sql_records_database_error_instead_of_raising() -> None:
    state = initial_state("question")
    state["current"] = SubQueryAction(action="subquery", subquery="question", sql="SELECT * FROM no_such_table")

    update = run_sql(state, make_reader_session())

    assert "no such table" in update["sql_error"]
    assert update["errors"] == [update["sql_error"]]


def test_union_drops_items_already_accumulated() -> None:
    first = MissingFiling("MSFT", 2024, 3)
    second = MissingFiling("MSFT", 2024, 2)

    assert union([first], [first, second, second]) == [first, second]
