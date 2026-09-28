from __future__ import annotations

from pydantic import BaseModel


class DocumentChunkImportResponse(BaseModel):
    ticker: str
    year: int
    quarter: int
    chunk_count: int
    status: str
