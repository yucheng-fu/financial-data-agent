from __future__ import annotations

from pydantic import BaseModel


class ImportedChunksResponse(BaseModel):
    """The chunk import outcome of one filing."""

    document_type: str
    period_type: str
    chunk_count: int
    status: str


class DocumentChunkImportResponse(BaseModel):
    ticker: str
    reporting_year: int
    reporting_quarter: int
    filings: list[ImportedChunksResponse]
