from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from financial_data_agent.api.main import app
from financial_data_agent.api.v1 import chat as chat_route
from financial_data_agent.services import chat as chat_service

SQL = "SELECT count(*) FROM companies"


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
    return "count\n503"


def tool_call_message() -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": "query_database", "args": {"sql": SQL}, "id": "call-1"}])


def use_fakes(monkeypatch: pytest.MonkeyPatch, model: ToolCallingFakeChatModel) -> None:
    monkeypatch.setattr(chat_service, "get_chat_model", lambda: model)
    monkeypatch.setattr(chat_route, "query_database", query_database)


def test_chat_route_returns_answer_and_sql_step(monkeypatch: pytest.MonkeyPatch) -> None:
    model = ToolCallingFakeChatModel(
        messages=iter([tool_call_message(), AIMessage(content="There are 503 companies.")])
    )
    use_fakes(monkeypatch, model)

    response = TestClient(app).post("/api/v1/chat", json={"message": "How many companies are there?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "There are 503 companies.",
        "steps": [{"tool": "query_database", "arguments": {"sql": SQL}, "result": "count\n503"}],
    }


def test_chat_route_returns_422_when_step_limit_is_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fakes(monkeypatch, ToolCallingFakeChatModel(messages=(tool_call_message() for _ in count())))

    response = TestClient(app).post("/api/v1/chat", json={"message": "Loop forever"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "No answer within 10 steps"
    assert detail["steps"]
    assert detail["steps"][0] == {"tool": "query_database", "arguments": {"sql": SQL}, "result": "count\n503"}
