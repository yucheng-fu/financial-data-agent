from __future__ import annotations

from pydantic import BaseModel


class CompanyImportRequest(BaseModel):
    """Request payload for importing a single S&P 500 company."""

    ticker: str

