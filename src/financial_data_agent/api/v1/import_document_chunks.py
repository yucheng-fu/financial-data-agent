from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.document_chunks import DocumentChunkImportRequest
from financial_data_agent.api.responses.document_chunks import DocumentChunkImportResponse, ImportedChunksResponse
from financial_data_agent.db.database import get_session
from financial_data_agent.services.document_chunk_import import (
    DocumentChunkImportService,
    EmbeddingDimensionError,
    FilingContentNotFoundError,
)
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import DocumentNotFoundError

router = APIRouter(tags=["Import document chunks"])


@router.post("/document-chunks/import", summary="Chunk and embed the stored filings reported in a quarter")
def import_document_chunks(
    request: DocumentChunkImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkImportResponse:
    """Chunk the stored markdown of the filings reported in a quarter, embed the chunks, and save them to the database.

    Args:
        request: Ticker, the calendar year and quarter the filings were reported in, and whether to replace
            existing chunks.
        session: Database session dependency.

    Returns:
        The ticker, the reporting period, and each filing with its period type, the number of stored chunks,
        and what was done.

    Raises:
        HTTPException: 404 if the company, filing, or its stored markdown is missing,
            422 if the embedding dimension is wrong.
    """
    try:
        result = DocumentChunkImportService(session).import_chunks(
            ticker=request.ticker,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            force=request.force,
        )
    except (CompanyNotFoundError, DocumentNotFoundError, FilingContentNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except EmbeddingDimensionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return DocumentChunkImportResponse(
        ticker=result.ticker,
        reporting_year=result.reporting_year,
        reporting_quarter=result.reporting_quarter,
        filings=[
            ImportedChunksResponse(
                document_type=item.document_type,
                period_type=item.period_type,
                chunk_count=item.chunk_count,
                status=item.status,
            )
            for item in result.filings
        ],
    )
