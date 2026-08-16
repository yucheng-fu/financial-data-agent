from __future__ import annotations

from pydantic import BaseModel


class FilingImportResponse(BaseModel):
    """Response payload for a filing download request."""

    ticker: str
    year: int
    quarter: int
    file_path: str

