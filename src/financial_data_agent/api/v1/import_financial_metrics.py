from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.financial_metrics import (
    FinancialMetricsImportRequest,
)
from financial_data_agent.api.responses.financial_metrics import (
    FinancialMetricsImportResponse,
)
from financial_data_agent.db.database import get_session
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import (
    DocumentNotFoundError,
    FinancialMetricsImportService,
    MetricsExtractionError,
)

router = APIRouter(tags=["Import financial metrics"])


@router.post("/financial-metrics/import", summary="Import financial metrics for a filing")
def import_financial_metrics(
    request: FinancialMetricsImportRequest,
    session: Annotated[Session, Depends(get_session)],
) -> FinancialMetricsImportResponse:
    """Extract the financial metrics of a stored filing and save them to the database."""
    try:
        result = FinancialMetricsImportService(session).import_metrics(
            ticker=request.ticker, year=request.year, quarter=request.quarter
        )
    except (CompanyNotFoundError, DocumentNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except MetricsExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return FinancialMetricsImportResponse(
        ticker=result.ticker, year=result.year, quarter=result.quarter, status=result.status
    )
