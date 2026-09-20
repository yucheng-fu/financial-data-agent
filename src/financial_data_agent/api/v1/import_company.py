from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.companies import CompanyImportRequest
from financial_data_agent.api.responses.companies import (
    CompanyImportResponse,
    CompanyImportSummaryResponse,
)
from financial_data_agent.db.database import get_session
from financial_data_agent.services.company_import import (
    CompanyImportService,
    CompanyMappingError,
    CompanyNotFoundError,
)

router = APIRouter(tags=["Import company data"])


@router.post("/companies/sp500/import", summary="Import all S&P 500 companies")
def import_sp500_companies(
    session: Annotated[Session, Depends(get_session)],
) -> CompanyImportSummaryResponse:
    """Fetch the current S&P 500 table from Wikipedia and sync it into the database.

    Args:
        session: Database session dependency.

    Returns:
        Number of companies created, updated, and in total.
    """
    summary = CompanyImportService(session).import_all()
    return CompanyImportSummaryResponse(created=summary.created, updated=summary.updated, total=summary.total)


@router.post("/companies/sp500/import/single", summary="Import a single S&P 500 company")
def import_sp500_company(
    request: CompanyImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CompanyImportResponse:
    """Fetch a single S&P 500 company from Wikipedia and sync it into the database.

    Args:
        request: Ticker of the company to import.
        session: Database session dependency.

    Returns:
        The ticker and whether the company was created or updated.

    Raises:
        HTTPException: 404 if the ticker is not in the S&P 500 table, 422 if it cannot be mapped.
    """
    try:
        result = CompanyImportService(session).import_one(request.ticker)
    except CompanyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except CompanyMappingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return CompanyImportResponse(ticker=result.ticker, status=result.status)
