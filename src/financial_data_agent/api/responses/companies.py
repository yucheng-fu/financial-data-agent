from __future__ import annotations

from pydantic import BaseModel


class CompanyImportSummaryResponse(BaseModel):
    """Response payload for bulk S&P 500 company imports."""

    created: int
    updated: int
    total: int


class CompanyImportResponse(BaseModel):
    """Response payload for a single S&P 500 company import."""

    ticker: str
    status: str
