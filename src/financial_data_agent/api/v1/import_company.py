from __future__ import annotations

from datetime import date

import polars as pl
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.database import get_session
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.ingestion.sp500 import SP500Fetcher

router = APIRouter(tags=["Import company data"])


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        return date.fromisoformat(value.strip())
    return None


def _row_to_company_dto(row: dict[str, object]) -> CompanyDTO:
    return CompanyDTO(
        ticker=row.get("Symbol") if isinstance(row.get("Symbol"), str) else None,
        name=row.get("Security") if isinstance(row.get("Security"), str) else None,
        gics_sector=(
            row.get("GICS Sector") if isinstance(row.get("GICS Sector"), str) else None
        ),
        gics_sub_industry=(
            row.get("GICS Sub-Industry")
            if isinstance(row.get("GICS Sub-Industry"), str)
            else None
        ),
        date_added=_parse_date(row.get("Date added")),
        cik=row.get("CIK") if isinstance(row.get("CIK"), str) else row.get("CIK"),
        supplied_fields=frozenset(
            {
                "ticker",
                "name",
                "gics_sector",
                "gics_sub_industry",
                "date_added",
                "cik",
            }
        ),
    )


@router.post("/companies/sp500/import", summary="Import all S&P 500 companies")
def import_sp500_companies(session: Session = Depends(get_session)) -> dict[str, int]:
    """Fetch the current S&P 500 table from Wikipedia and sync it into the database."""
    fetcher = SP500Fetcher()
    frame = fetcher.fetch(save_parquet=True)
    repository = CompanyRepository(session)

    created = 0
    updated = 0
    rows = frame.to_dicts()
    for row in rows:
        if not isinstance(row, dict):
            continue

        company_dto = _row_to_company_dto(row)
        if not company_dto.ticker or not company_dto.name:
            continue

        existing_company = repository.get_by_ticker(company_dto.ticker)
        if existing_company is None:
            repository.create(company_dto)
            created += 1
            continue

        repository.update(existing_company, company_dto)
        updated += 1

    return {"created": created, "updated": updated, "total": created + updated}


@router.post(
    "/companies/sp500/import/{ticker}", summary="Import a single S&P 500 company"
)
def import_sp500_company(
    ticker: str,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Fetch a single S&P 500 company from Wikipedia and sync it into the database."""
    fetcher = SP500Fetcher()
    frame = fetcher.fetch(save_parquet=False)
    repository = CompanyRepository(session)

    matches = frame.filter(pl.col("Symbol") == ticker.upper())
    if matches.is_empty():
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {ticker.upper()} was not found in the S&P 500 table",
        )

    company_dto = _row_to_company_dto(matches.to_dicts()[0])
    if not company_dto.ticker or not company_dto.name:
        raise HTTPException(
            status_code=422,
            detail=f"Ticker {ticker.upper()} could not be mapped to a company record",
        )

    existing_company = repository.get_by_ticker(company_dto.ticker)
    if existing_company is None:
        repository.create(company_dto)
        action = "created"
    else:
        repository.update(existing_company, company_dto)
        action = "updated"

    return {"ticker": company_dto.ticker, "status": action}
