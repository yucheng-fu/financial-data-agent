from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from financial_data_agent.api.responses.document_chunks import DocumentChunkImportResponse


class QueryDatabaseResponse(BaseModel):
    """Rows returned by the query_database tool, or the error that stopped the call."""

    rows: list[dict[str, Any]] = []
    truncated: bool = False
    error: str | None = None


class CitationResponse(BaseModel):
    """A filing an answer was based on; `chunk_index` is empty for metrics."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    reporting_year: int
    reporting_quarter: int
    period_type: str
    accession_number: str | None = None
    chunk_index: int | None = None
    heading_path: str | None = None


class MissingFilingResponse(BaseModel):
    """A filing a question needed that is not stored."""

    ticker: str
    year: int
    quarter: int


class TableRAGResponse(BaseModel):
    """The answer of the table_rag tool with its citations, or the error that stopped the call."""

    answer: str | None = None
    citations: list[CitationResponse] = []
    missing: list[MissingFilingResponse] = []
    error: str | None = None


class FilingCoverageResponse(BaseModel):
    """A stored filing and how many chunks it has."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    period_type: str
    chunk_count: int


class ListAvailableFilingsResponse(BaseModel):
    """The filings stored in the database."""

    filings: list[FilingCoverageResponse]


class AcquireFilingResponse(BaseModel):
    """The outcome of the acquire_filing tool, or the error that stopped the call."""

    result: DocumentChunkImportResponse | None = None
    error: str | None = None


class ChatStepResponse(BaseModel):
    """One tool call the agent made while answering; `result` is the tool's JSON output."""

    tool: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class TokenUsageResponse(BaseModel):
    """Tokens spent on chat model calls while answering."""

    input_tokens: int
    output_tokens: int


class ChatResponse(BaseModel):
    """Response payload with the agent's answer, its citations, the tool calls behind it and the tokens spent."""

    answer: str
    citations: list[CitationResponse]
    steps: list[ChatStepResponse]
    usage: TokenUsageResponse
