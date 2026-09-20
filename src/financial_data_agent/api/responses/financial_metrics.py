from __future__ import annotations

from pydantic import BaseModel


class FinancialMetricsImportResponse(BaseModel):
    """Response payload for a financial metrics import request."""

    ticker: str
    year: int
    quarter: int
    status: str
