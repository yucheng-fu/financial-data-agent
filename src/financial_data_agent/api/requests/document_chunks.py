from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentChunkImportRequest(BaseModel):
    ticker: str
    reporting_year: int = 2020
    reporting_quarter: int = Field(ge=1, le=4)
    force: bool = False
