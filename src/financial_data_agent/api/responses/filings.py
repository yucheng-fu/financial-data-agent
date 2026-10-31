from __future__ import annotations

from pydantic import BaseModel


class ImportedFilingResponse(BaseModel):
    """A downloaded filing and whether it reports on a quarter or a full year."""

    document_type: str
    period_type: str
    file_path: str


class FilingImportResponse(BaseModel):
    """Response payload for a filing download request."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    filings: list[ImportedFilingResponse]
