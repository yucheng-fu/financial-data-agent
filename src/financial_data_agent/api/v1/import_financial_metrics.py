from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.financial_metrics import FinancialMetricsImportRequest
from financial_data_agent.services.financial_metrics_import import FinancialMetricsImportService

router = APIRouter(tags=["Import financial metrics"])


def import_financial_metrics(
    request: FinancialMetricsImportRequest, session: Session
) -> None:
    """Import financial metrics for a filing."""
    FinancialMetricsImportService(session).import_metrics(
        ticker=request.ticker,
        year=request.year,
        quarter=request.quarter,
    )
