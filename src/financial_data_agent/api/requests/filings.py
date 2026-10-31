from __future__ import annotations

from pydantic import BaseModel, Field


class FilingImportRequest(BaseModel):
    """Request payload for downloading the SEC filings reported in a calendar quarter."""

    ticker: str
    reporting_year: int = 2020
    reporting_quarter: int = Field(ge=1, le=4)
