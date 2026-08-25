from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from financial_data_agent.api.requests.filings import FinancialMetricsImportRequest

router = APIRouter(tags=["Import financial metrics"])


def import_financial_metrics(
    request: FinancialMetricsImportRequest, session: Session
) -> None:
    pass
