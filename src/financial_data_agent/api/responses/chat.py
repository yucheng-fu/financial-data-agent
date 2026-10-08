from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QueryDatabaseResponse(BaseModel):
    """Rows returned by the query_database tool, or the error that stopped the call."""

    rows: list[dict[str, Any]] = []
    truncated: bool = False
    error: str | None = None


class ChatStepResponse(BaseModel):
    """One tool call the agent made while answering."""

    tool: str
    arguments: dict[str, Any]
    result: QueryDatabaseResponse


class ChatResponse(BaseModel):
    """Response payload with the agent's answer and the tool calls behind it."""

    answer: str
    steps: list[ChatStepResponse]
