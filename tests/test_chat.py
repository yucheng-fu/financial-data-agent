from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata

from financial_data_agent.api.main import app
from financial_data_agent.api.responses.chat import QueryDatabaseResponse
from financial_data_agent.api.v1 import chat as chat_route
from financial_data_agent.services import chat as chat_service

SQL = "SELECT count(*) FROM companies"
RESULT = {"rows": [{"count": 503}], "truncated": False, "error": None}


class ToolCallingFakeChatModel(GenericFakeChatModel):
    """Scripted chat model that accepts tool bindings, which the stock fake refuses."""

    def bind_tools(self, tools: Sequence[Callable[..., Any]], **kwargs: Any) -> ToolCallingFakeChatModel:
        return self


def query_database(sql: str) -> str:
    """Run one read-only SQL query.

    Args:
        sql: The SQL to run.

    Returns:
        The result rows.
    """
    return QueryDatabaseResponse.model_validate(RESULT).model_dump_json()


def usage(input_tokens: int, output_tokens: int) -> UsageMetadata:
    return UsageMetadata(
        input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens
    )


def tool_call_message(tool: str = "query_database") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": tool, "args": {"sql": SQL}, "id": "call-1"}],
        usage_metadata=usage(100, 20),
    )


def use_fakes(monkeypatch: pytest.MonkeyPatch, model: ToolCallingFakeChatModel) -> None:
    monkeypatch.setattr(chat_service, "get_chat_model", lambda: model)
    monkeypatch.setattr(chat_route, "query_database", query_database)


def test_chat_route_returns_answer_and_sql_step(monkeypatch: pytest.MonkeyPatch) -> None:
    model = ToolCallingFakeChatModel(
        messages=iter(
            [tool_call_message(), AIMessage(content="There are 503 companies.", usage_metadata=usage(150, 8))]
        )
    )
    use_fakes(monkeypatch, model)

    response = TestClient(app).post("/api/v1/chat", json={"message": "How many companies are there?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "There are 503 companies.",
        "citations": [],
        "steps": [{"tool": "query_database", "arguments": {"sql": SQL}, "result": RESULT}],
        "usage": {"input_tokens": 250, "output_tokens": 28},
    }


def test_chat_route_reports_zero_usage_when_provider_omits_it(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, ToolCallingFakeChatModel(messages=iter([AIMessage(content="Hello.")])))

    response = TestClient(app).post("/api/v1/chat", json={"message": "Hi"})

    assert response.json()["usage"] == {"input_tokens": 0, "output_tokens": 0}


def test_chat_route_reports_unknown_tool_call_as_step_error(monkeypatch: pytest.MonkeyPatch) -> None:
    model = ToolCallingFakeChatModel(
        messages=iter([tool_call_message("drop_tables"), AIMessage(content="I cannot do that.")])
    )
    use_fakes(monkeypatch, model)

    response = TestClient(app).post("/api/v1/chat", json={"message": "Drop everything"})

    assert response.status_code == 200
    result = response.json()["steps"][0]["result"]
    assert result["error"].startswith("Error: drop_tables is not a valid tool")


def test_chat_route_returns_422_when_step_limit_is_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, ToolCallingFakeChatModel(messages=(tool_call_message() for _ in count())))

    response = TestClient(app).post("/api/v1/chat", json={"message": "Loop forever"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "No answer within 10 steps"
    assert detail["steps"]
    assert detail["steps"][0] == {"tool": "query_database", "arguments": {"sql": SQL}, "result": RESULT}
    assert detail["usage"] == {"input_tokens": 100 * len(detail["steps"]), "output_tokens": 20 * len(detail["steps"])}


FILING_ROW = {
    "ticker": "NVDA",
    "reporting_year": 2020,
    "reporting_quarter": 2,
    "period_type": "quarterly",
    "accession_number": "0001045810-20-000010",
    "revenue": "3080000000.00",
}


def test_chat_route_cites_the_filing_behind_a_metric_row_without_accession_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = {key: value for key, value in FILING_ROW.items() if key != "accession_number"}

    def query_database(sql: str) -> str:
        """Run one read-only SQL query.

        Args:
            sql: The SQL to run.

        Returns:
            The result rows.
        """
        return json.dumps({"rows": [row], "truncated": False, "error": None})

    model = ToolCallingFakeChatModel(
        messages=iter([tool_call_message(), AIMessage(content="$3.08B.", usage_metadata=usage(10, 2))])
    )
    use_fakes(monkeypatch, model)
    monkeypatch.setattr(chat_route, "query_database", query_database)

    body = TestClient(app).post("/api/v1/chat", json={"message": "NVDA revenue?"}).json()

    assert body["citations"] == [
        {
            "ticker": "NVDA",
            "reporting_year": 2020,
            "reporting_quarter": 2,
            "period_type": "quarterly",
            "accession_number": None,
            "chunk_index": None,
            "heading_path": None,
        }
    ]


QUESTION = "Compare Apple and Microsoft revenue in Q3 2024."
CITATION = {
    "ticker": "AAPL",
    "reporting_year": 2024,
    "reporting_quarter": 3,
    "period_type": "quarterly",
    "accession_number": "0000320193-24-000081",
    "chunk_index": 7,
    "heading_path": None,
}


class FakeAcquirer:
    calls: list[tuple[str, int, int]] = []

    def acquire_filing(self, ticker: str, reporting_year: int, reporting_quarter: int) -> str:
        """Download a filing.

        Args:
            ticker: Ticker symbol.
            reporting_year: Calendar year.
            reporting_quarter: Calendar quarter.

        Returns:
            The outcome as JSON.
        """
        self.calls.append((ticker, reporting_year, reporting_quarter))
        return json.dumps({"result": None, "error": None})


def named_call(tool: str, args: dict[str, Any], call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": tool, "args": args, "id": call_id}], usage_metadata=usage(10, 2))


def test_chat_route_acquires_a_missing_filing_once_then_retries_table_rag(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(
        [
            {
                "answer": "Only Apple found.",
                "citations": [CITATION],
                "missing": [{"ticker": "MSFT", "year": 2024, "quarter": 3}],
            },
            {"answer": "Apple led.", "citations": [CITATION], "missing": []},
        ]
    )

    def table_rag(question: str) -> str:
        """Answer from the filings.

        Args:
            question: The question.

        Returns:
            The answer as JSON.
        """
        return json.dumps({"error": None, **next(answers)})

    FakeAcquirer.calls = []
    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                named_call("table_rag", {"question": QUESTION}, "call-1"),
                named_call(
                    "acquire_filing", {"ticker": "MSFT", "reporting_year": 2024, "reporting_quarter": 3}, "call-2"
                ),
                named_call("table_rag", {"question": QUESTION}, "call-3"),
                AIMessage(content="Apple led.", usage_metadata=usage(10, 2)),
            ]
        )
    )
    use_fakes(monkeypatch, model)
    monkeypatch.setattr(chat_route, "table_rag", table_rag)
    monkeypatch.setattr(chat_route, "FilingAcquirer", FakeAcquirer)

    response = TestClient(app).post("/api/v1/chat", json={"message": QUESTION})

    body = response.json()
    assert response.status_code == 200
    assert [step["tool"] for step in body["steps"]] == ["table_rag", "acquire_filing", "table_rag"]
    assert FakeAcquirer.calls == [("MSFT", 2024, 3)]
    assert body["citations"] == [CITATION]


ANNUAL_ROW = {
    "ticker": "NVDA",
    "reporting_year": 2020,
    "reporting_quarter": 1,
    "period_type": "annual",
    "period_of_report": "2020-01-26",
    "revenue": "10918000000.00",
}
EARLIER_QUARTERLY_ROW = {
    "ticker": "NVDA",
    "reporting_year": 2019,
    "reporting_quarter": 4,
    "period_type": "quarterly",
    "period_of_report": "2019-10-27",
    "revenue": "3014000000.00",
}
NVDA_QUESTION = "What is the revenue of NVDA that was reported in 2020 Q1?"


def citation_for(row: dict[str, str | int]) -> dict[str, str | int | None]:
    return {
        "ticker": row["ticker"],
        "reporting_year": row["reporting_year"],
        "reporting_quarter": row["reporting_quarter"],
        "period_type": row["period_type"],
        "accession_number": None,
        "chunk_index": None,
        "heading_path": None,
    }


def test_chat_route_cites_the_10k_and_the_earlier_10q_for_an_annual_only_quarter_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def query_database(sql: str) -> str:
        """Run one read-only SQL query.

        Args:
            sql: The SQL to run.

        Returns:
            The result rows.
        """
        return json.dumps({"rows": [ANNUAL_ROW, EARLIER_QUARTERLY_ROW], "truncated": False, "error": None})

    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                named_call("query_database", {"sql": SQL}, "call-1"),
                AIMessage(content="Full year $10.918B; quarter ended 2019-10-27 $3.014B.", usage_metadata=usage(10, 2)),
            ]
        )
    )
    use_fakes(monkeypatch, model)
    monkeypatch.setattr(chat_route, "query_database", query_database)

    body = TestClient(app).post("/api/v1/chat", json={"message": NVDA_QUESTION}).json()

    assert [step["tool"] for step in body["steps"]] == ["query_database"]
    assert body["citations"] == [citation_for(ANNUAL_ROW), citation_for(EARLIER_QUARTERLY_ROW)]


def test_chat_route_acquires_the_earlier_10q_once_then_retries_the_query(monkeypatch: pytest.MonkeyPatch) -> None:
    results = iter([[ANNUAL_ROW], [ANNUAL_ROW, EARLIER_QUARTERLY_ROW]])

    def query_database(sql: str) -> str:
        """Run one read-only SQL query.

        Args:
            sql: The SQL to run.

        Returns:
            The result rows.
        """
        return json.dumps({"rows": next(results), "truncated": False, "error": None})

    FakeAcquirer.calls = []
    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                named_call("query_database", {"sql": SQL}, "call-1"),
                named_call(
                    "acquire_filing", {"ticker": "NVDA", "reporting_year": 2019, "reporting_quarter": 4}, "call-2"
                ),
                named_call("query_database", {"sql": SQL}, "call-3"),
                AIMessage(content="Full year $10.918B; quarter ended 2019-10-27 $3.014B.", usage_metadata=usage(10, 2)),
            ]
        )
    )
    use_fakes(monkeypatch, model)
    monkeypatch.setattr(chat_route, "query_database", query_database)
    monkeypatch.setattr(chat_route, "FilingAcquirer", FakeAcquirer)

    body = TestClient(app).post("/api/v1/chat", json={"message": NVDA_QUESTION}).json()

    assert [step["tool"] for step in body["steps"]] == ["query_database", "acquire_filing", "query_database"]
    assert FakeAcquirer.calls == [("NVDA", 2019, 4)]
    assert body["citations"] == [citation_for(ANNUAL_ROW), citation_for(EARLIER_QUARTERLY_ROW)]


def test_chat_route_cites_every_source_filing_of_get_fourth_quarter(monkeypatch: pytest.MonkeyPatch) -> None:
    sources = [
        {"ticker": "NVDA", "reporting_year": 2020, "reporting_quarter": 1, "period_type": "annual"},
        {"ticker": "NVDA", "reporting_year": 2019, "reporting_quarter": 2, "period_type": "quarterly"},
        {"ticker": "NVDA", "reporting_year": 2019, "reporting_quarter": 3, "period_type": "quarterly"},
        {"ticker": "NVDA", "reporting_year": 2019, "reporting_quarter": 4, "period_type": "quarterly"},
    ]

    def get_fourth_quarter(ticker: str, reporting_year: int, reporting_quarter: int) -> str:
        """Derive the fiscal fourth quarter.

        Args:
            ticker: Ticker symbol.
            reporting_year: Calendar year.
            reporting_quarter: Calendar quarter.

        Returns:
            The derived quarter as JSON.
        """
        return json.dumps(
            {
                "ticker": ticker,
                "fourth_quarter": {"revenue": "3105000000.00"},
                "previous_quarter": {"revenue": "3014000000.00"},
                "sources": sources,
                "error": None,
            }
        )

    model = ToolCallingFakeChatModel(
        messages=iter(
            [
                named_call(
                    "get_fourth_quarter", {"ticker": "NVDA", "reporting_year": 2020, "reporting_quarter": 1}, "call-1"
                ),
                AIMessage(content="Revenue rose $91M (+3.0%).", usage_metadata=usage(10, 2)),
            ]
        )
    )
    use_fakes(monkeypatch, model)
    monkeypatch.setattr(chat_route, "get_fourth_quarter", get_fourth_quarter)

    body = (
        TestClient(app)
        .post("/api/v1/chat", json={"message": "Revenue change in 2020 Q1 from the previous quarter?"})
        .json()
    )

    assert [step["tool"] for step in body["steps"]] == ["get_fourth_quarter"]
    assert body["citations"] == [citation_for(source) for source in sources]
