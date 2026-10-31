from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.filings import FilingImportRequest
from financial_data_agent.api.responses.filings import FilingImportResponse, ImportedFilingResponse
from financial_data_agent.db.database import get_session
from financial_data_agent.services.filing_import import (
    CompanyNotFoundError,
    FilingImportService,
    FilingNotFoundError,
)

router = APIRouter(tags=["Import filings"])


@router.post("/filings/import", summary="Download the SEC 10-Q and 10-K filings reported in a quarter")
def download_filing(
    request: FilingImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FilingImportResponse:
    """Download the SEC filings a company reported in the requested calendar quarter.

    Args:
        request: Ticker and the calendar year and quarter the filings were reported in.
        session: Database session dependency.

    Returns:
        The ticker, the reporting period, and each filing with its period type and file path.

    Raises:
        HTTPException: 404 if the company is not in the database or the SEC has no matching filing.
    """
    try:
        result = FilingImportService(session).import_filings(
            ticker=request.ticker, reporting_year=request.reporting_year, reporting_quarter=request.reporting_quarter
        )
    except (CompanyNotFoundError, FilingNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return FilingImportResponse(
        ticker=result.ticker,
        reporting_year=result.reporting_year,
        reporting_quarter=result.reporting_quarter,
        filings=[
            ImportedFilingResponse(
                document_type=filing.document_type,
                period_type=filing.period_type,
                file_path=filing.file_path,
            )
            for filing in result.filings
        ],
    )
