from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request payload for asking the agent a question."""

    message: str = Field(min_length=1)
