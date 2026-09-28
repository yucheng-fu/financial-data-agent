from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.document_chunks import DocumentChunkImportRequest
from financial_data_agent.api.responses.document_chunks import DocumentChunkImportResponse
from financial_data_agent.db.database import get_session
from financial_data_agent.services.document_chunk_import import (
    DocumentChunkImportService,
    EmbeddingDimensionError,
    FilingContentNotFoundError,
)
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import DocumentNotFoundError

router = APIRouter(tags=["Import document chunks"])


@router.post("/document-chunks/import", summary="Chunk and embed a stored filing")
def import_document_chunks(
    request: DocumentChunkImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkImportResponse:
    """Chunk the stored markdown of a filing, embed the chunks, and save them to the database.

    Args:
        request: Ticker, year, quarter, and whether to replace existing chunks.
        session: Database session dependency.

    Returns:
        The ticker, period, the number of stored chunks, and what was done.

    Raises:
        HTTPException: 404 if the company, filing, or its stored markdown is missing,
            422 if the embedding dimension is wrong.
    """
    try:
        result = DocumentChunkImportService(session).import_chunks(
            ticker=request.ticker, year=request.year, quarter=request.quarter, force=request.force
        )
    except (CompanyNotFoundError, DocumentNotFoundError, FilingContentNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except EmbeddingDimensionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return DocumentChunkImportResponse(
        ticker=result.ticker,
        year=result.year,
        quarter=result.quarter,
        chunk_count=result.chunk_count,
        status=result.status,
    )
