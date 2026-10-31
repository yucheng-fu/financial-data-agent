from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.financial_metrics import (
    FinancialMetricsImportRequest,
)
from financial_data_agent.api.responses.financial_metrics import (
    FinancialMetricsImportResponse,
    ImportedMetricsResponse,
)
from financial_data_agent.db.database import get_session
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import (
    DocumentNotFoundError,
    FinancialMetricsImportService,
    MetricsExtractionError,
)

router = APIRouter(tags=["Import financial metrics"])


@router.post("/financial-metrics/import", summary="Import financial metrics for the filings reported in a quarter")
def import_financial_metrics(
    request: FinancialMetricsImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FinancialMetricsImportResponse:
    """Extract the financial metrics of the stored filings reported in a quarter and save them to the database.

    Args:
        request: Ticker and the calendar year and quarter the filings were reported in.
        session: Database session dependency.

    Returns:
        The ticker, the reporting period, and each filing with its period type and whether its metrics were
        created or updated.

    Raises:
        HTTPException: 404 if the company or filing is not in the database, 422 if the SEC data is unavailable.
    """
    try:
        result = FinancialMetricsImportService(session).import_metrics(
            ticker=request.ticker,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
        )
    except (CompanyNotFoundError, DocumentNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except MetricsExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return FinancialMetricsImportResponse(
        ticker=result.ticker,
        reporting_year=result.reporting_year,
        reporting_quarter=result.reporting_quarter,
        filings=[
            ImportedMetricsResponse(document_type=item.document_type, period_type=item.period_type, status=item.status)
            for item in result.filings
        ],
    )
