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


class TokenUsageResponse(BaseModel):
    """Tokens spent on chat model calls while answering."""

    input_tokens: int
    output_tokens: int


class ChatResponse(BaseModel):
    """Response payload with the agent's answer, the tool calls behind it and the tokens spent."""

    answer: str
    steps: list[ChatStepResponse]
    usage: TokenUsageResponse
