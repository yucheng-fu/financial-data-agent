from __future__ import annotations

from pydantic import BaseModel, Field


class FilingImportRequest(BaseModel):
    """Request payload for downloading a single SEC filing."""

    ticker: str
    year: int = 2020
    quarter: int = Field(ge=1, le=4)
