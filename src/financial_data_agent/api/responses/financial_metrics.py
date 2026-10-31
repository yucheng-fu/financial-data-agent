from __future__ import annotations

from pydantic import BaseModel


class ImportedMetricsResponse(BaseModel):
    """The metrics import outcome of one filing."""

    document_type: str
    period_type: str
    status: str


class FinancialMetricsImportResponse(BaseModel):
    """Response payload for a financial metrics import request."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    filings: list[ImportedMetricsResponse]
