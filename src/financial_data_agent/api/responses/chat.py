from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatStepResponse(BaseModel):
    """One tool call the agent made while answering."""

    tool: str
    arguments: dict[str, Any]
    result: str


class ChatResponse(BaseModel):
    """Response payload with the agent's answer and the tool calls behind it."""

    answer: str
    steps: list[ChatStepResponse]
