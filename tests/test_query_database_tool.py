from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import pytest
from sqlalchemy.exc import ProgrammingError

from financial_data_agent.api.tools import query_database as tool_module
from financial_data_agent.services.sql_query import SQLQueryResult


def patch_execution(monkeypatch: pytest.MonkeyPatch, outcome: SQLQueryResult | Exception) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []

    def fake_execute_llm_sql(session: Any, sql: str, row_limit: int) -> SQLQueryResult:
        calls.append((sql, row_limit))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(tool_module, "get_llm_reader_session_factory", lambda: lambda: nullcontext(object()))
    monkeypatch.setattr(tool_module, "execute_llm_sql", fake_execute_llm_sql)
    return calls


def test_query_database_formats_columns_and_rows_with_the_chat_row_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SQLQueryResult(
        columns=["ticker", "name"], rows=[("AAPL", "Apple Inc."), ("MSFT", "Microsoft")], truncated=False
    )
    calls = patch_execution(monkeypatch, result)

    output = tool_module.query_database("SELECT ticker, name FROM companies")

    assert output == "ticker | name\nAAPL | Apple Inc.\nMSFT | Microsoft"
    assert calls == [("SELECT ticker, name FROM companies", tool_module.CHAT_SQL_ROW_LIMIT)]


def test_query_database_notes_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_execution(monkeypatch, SQLQueryResult(columns=["id"], rows=[(1,), (2,)], truncated=True))

    output = tool_module.query_database("SELECT id FROM companies")

    assert output.endswith("(truncated to the first 2 rows)")


def test_query_database_returns_database_errors_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    error = ProgrammingError(
        "SELECT * FROM conversations", None, Exception("permission denied for table conversations")
    )
    patch_execution(monkeypatch, error)

    output = tool_module.query_database("SELECT * FROM conversations")

    assert output == "SQL error: permission denied for table conversations"
