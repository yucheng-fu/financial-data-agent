from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.filings import FilingImportRequest
from financial_data_agent.api.responses.filings import FilingImportResponse
from financial_data_agent.db.database import get_session
from financial_data_agent.services.filing_import import (
    CompanyNotFoundError,
    FilingImportService,
    FilingNotFoundError,
)

router = APIRouter(tags=["Import filings"])


@router.post("/filings/import", summary="Download a SEC 10-Q filing")
def download_filing(
    request: FilingImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FilingImportResponse:
    """Download a SEC filing for the requested ticker, year, and quarter.

    Args:
        request: Ticker, year, and quarter of the filing.
        session: Database session dependency.

    Returns:
        The ticker, period, and file path of the downloaded filing.

    Raises:
        HTTPException: 404 if the company is not in the database or the SEC has no matching filing.
    """
    try:
        result = FilingImportService(session).import_filing(
            ticker=request.ticker, year=request.year, quarter=request.quarter
        )
    except (CompanyNotFoundError, FilingNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return FilingImportResponse(
        ticker=result.ticker,
        year=result.year,
        quarter=result.quarter,
        file_path=result.file_path,
    )
