from __future__ import annotations

from pydantic import BaseModel, Field


class FinancialMetricsImportRequest(BaseModel):
    """Request payload for importing the financial metrics of the filings reported in a calendar quarter."""

    ticker: str
    reporting_year: int = 2020
    reporting_quarter: int = Field(ge=1, le=4)
