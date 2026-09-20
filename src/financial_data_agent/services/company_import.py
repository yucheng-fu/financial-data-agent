from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import polars as pl
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.ingestion.sp500 import SP500Fetcher


class CompanyNotFoundError(Exception):
    """Raised when a ticker is absent from the S&P 500 source."""


class CompanyMappingError(Exception):
    """Raised when S&P 500 source data cannot form a company record."""


@dataclass(frozen=True, slots=True)
class CompanyImportSummary:
    """Summary of a bulk company import."""

    created: int
    updated: int

    @property
    def total(self) -> int:
        """Return the number of companies created or updated."""
        return self.created + self.updated


@dataclass(frozen=True, slots=True)
class CompanyImportResult:
    """Outcome of a single company import."""

    ticker: str
    status: str


def _parse_date(value: object) -> date | None:
    """Convert a source date value into a date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        return date.fromisoformat(value.strip())
    return None


def _row_to_company_dto(row: dict[str, object]) -> CompanyDTO:
    """Map an S&P 500 source row to a company DTO."""
    return CompanyDTO(
        ticker=row.get("Symbol") if isinstance(row.get("Symbol"), str) else None,
        name=row.get("Security") if isinstance(row.get("Security"), str) else None,
        gics_sector=(row.get("GICS Sector") if isinstance(row.get("GICS Sector"), str) else None),
        gics_sub_industry=(
            row.get("GICS Sub-Industry") if isinstance(row.get("GICS Sub-Industry"), str) else None
        ),
        date_added=_parse_date(row.get("Date added")),
        cik=row.get("CIK") if isinstance(row.get("CIK"), str) else row.get("CIK"),
        supplied_fields=frozenset(
            {"ticker", "name", "gics_sector", "gics_sub_industry", "date_added", "cik"}
        ),
    )


class CompanyImportService:
    """Synchronize S&P 500 companies with the database."""

    def __init__(self, session: Session, fetcher: SP500Fetcher | None = None) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
            fetcher: Optional S&P 500 data fetcher.
        """
        self.repository = CompanyRepository(session)
        self.fetcher = fetcher or SP500Fetcher()

    def import_all(self) -> CompanyImportSummary:
        """Fetch and synchronize all available S&P 500 companies."""
        frame = self.fetcher.fetch(save_parquet=True)
        created = 0
        updated = 0
        for row in frame.to_dicts():
            if not isinstance(row, dict):
                continue
            company_dto = _row_to_company_dto(row)
            if not company_dto.ticker or not company_dto.name:
                continue
            existing_company = self.repository.get_by_ticker(company_dto.ticker)
            if existing_company is None:
                self.repository.create(company_dto)
                created += 1
            else:
                self.repository.update(existing_company, company_dto)
                updated += 1
        return CompanyImportSummary(created=created, updated=updated)

    def import_one(self, ticker: str) -> CompanyImportResult:
        """Fetch and synchronize one S&P 500 company.

        Raises:
            CompanyNotFoundError: If the ticker is not in the source data.
            CompanyMappingError: If the matching source row is incomplete.
        """
        normalized_ticker = ticker.upper()
        frame = self.fetcher.fetch(save_parquet=False)
        matches = frame.filter(pl.col("Symbol") == normalized_ticker)
        if matches.is_empty():
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the S&P 500 table")
        company_dto = _row_to_company_dto(matches.to_dicts()[0])
        if not company_dto.ticker or not company_dto.name:
            raise CompanyMappingError(f"Ticker {normalized_ticker} could not be mapped to a company record")
        existing_company = self.repository.get_by_ticker(company_dto.ticker)
        if existing_company is None:
            self.repository.create(company_dto)
            return CompanyImportResult(ticker=normalized_ticker, status="created")
        self.repository.update(existing_company, company_dto)
        return CompanyImportResult(ticker=normalized_ticker, status="updated")
