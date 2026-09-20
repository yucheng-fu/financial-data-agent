from __future__ import annotations

from pydantic import BaseModel, Field


class FinancialMetricsImportRequest(BaseModel):
    """Request payload for importing financial metrics for a single company."""

    ticker: str
    year: int = 2020
    quarter: int = Field(ge=1, le=4)
