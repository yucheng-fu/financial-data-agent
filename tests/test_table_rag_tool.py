from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from langgraph.errors import GraphRecursionError

from financial_data_agent.agent.tablerag.errors import DecompositionParseError
from financial_data_agent.agent.tablerag.graph import recursion_limit_for
from financial_data_agent.agent.tablerag.state import Citation, MissingFiling
from financial_data_agent.api.tools import table_rag as table_rag_module
from financial_data_agent.api.tools.table_rag import table_rag

CITATION = Citation("AAPL", 2024, 3, "quarterly", "0000320193-24-000081", 7, "Item 2 > Results")


class FakeGraph:
    def __init__(self, state: dict[str, Any] | Exception) -> None:
        self.state = state
        self.config: dict[str, Any] = {}

    def invoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.config = config
        if isinstance(self.state, Exception):
            raise self.state
        return self.state


def use_graph(monkeypatch: pytest.MonkeyPatch, graph: FakeGraph) -> None:
    monkeypatch.setattr(table_rag_module, "get_session_factory", lambda: MagicMock())
    monkeypatch.setattr(table_rag_module, "get_llm_reader_session_factory", lambda: MagicMock())
    monkeypatch.setattr(table_rag_module, "get_chat_model", lambda: MagicMock())
    monkeypatch.setattr(table_rag_module, "get_embedder", lambda: MagicMock())
    monkeypatch.setattr(table_rag_module, "build_tablerag_graph", lambda *args: graph)


def state(answer: str | None, missing: list[MissingFiling] | None = None) -> dict[str, Any]:
    return {"answer": answer, "citations": [CITATION], "missing": missing or []}


def test_table_rag_returns_answer_citations_and_missing_filings(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = FakeGraph(state("Revenue grew.", [MissingFiling("MSFT", 2024, 3)]))
    use_graph(monkeypatch, graph)

    result = json.loads(table_rag("Compare AAPL and MSFT revenue"))

    assert result["answer"] == "Revenue grew."
    assert result["citations"] == [
        {
            "ticker": "AAPL",
            "reporting_year": 2024,
            "reporting_quarter": 3,
            "period_type": "quarterly",
            "accession_number": "0000320193-24-000081",
            "chunk_index": 7,
            "heading_path": "Item 2 > Results",
        }
    ]
    assert result["missing"] == [{"ticker": "MSFT", "year": 2024, "quarter": 3}]
    assert result["error"] is None
    assert graph.config == {"recursion_limit": recursion_limit_for(table_rag_module.MAX_ITERATIONS)}


def test_table_rag_reports_error_when_no_answer_within_max_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    use_graph(monkeypatch, FakeGraph(state(None)))

    result = json.loads(table_rag("Hard question"))

    assert result["answer"] is None
    assert result["error"].startswith("No answer within")


@pytest.mark.parametrize("error", [GraphRecursionError("too many steps"), DecompositionParseError("not json")])
def test_table_rag_returns_graph_failures_as_error_text(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    use_graph(monkeypatch, FakeGraph(error))

    result = json.loads(table_rag("Anything"))

    assert result["error"].startswith("TableRAG failed:")
    assert result["answer"] is None
