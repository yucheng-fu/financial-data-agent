from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.ingestion.filings import FilingsFetcher


class CompanyNotFoundError(Exception):
    """Raised when a filing is requested for a company not in the database."""


class FilingNotFoundError(Exception):
    """Raised when no SEC filing exists for a requested period."""


@dataclass(frozen=True, slots=True)
class FilingImportResult:
    """Details of a downloaded and persisted filing."""

    ticker: str
    year: int
    quarter: int
    file_path: str


class FilingImportService:
    """Download and persist SEC filings."""

    def __init__(self, session: Session, fetcher: FilingsFetcher | None = None) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
            fetcher: Optional SEC filing fetcher.
        """
        self.session = session
        self.company_repository = CompanyRepository(session)
        self.document_repository = DocumentRepository(session)
        self.fetcher = fetcher or FilingsFetcher()

    def import_filing(self, ticker: str, year: int, quarter: int) -> FilingImportResult:
        """Download and persist a filing for a company and reporting period.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            FilingNotFoundError: If the SEC has no matching filing.
        """
        normalized_ticker = ticker.upper()
        company = self.company_repository.get_by_ticker(normalized_ticker)
        if company is None:
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the database")
        try:
            file_path, filing = self.fetcher.fetch_filing(
                ticker=ticker, form=["10-Q", "10-K"], quarter=quarter, year=year
            )
        except ValueError as error:
            raise FilingNotFoundError(
                f"SEC filing not found for {normalized_ticker} in {year} Q{quarter}"
            ) from error
        self.document_repository.create(
            DocumentDTO(
                company_id=company.id,
                accession_number=filing.accession_number,
                document_type=filing.form,
                year=year,
                quarter=quarter,
                filing_date=_parse_date(filing.filing_date),
                period_of_report=_parse_date(filing.period_of_report),
                raw_document_path=file_path.as_posix(),
                supplied_fields=frozenset(
                    {
                        "company_id", "accession_number", "document_type", "year", "quarter",
                        "filing_date", "period_of_report", "raw_document_path",
                    }
                ),
            )
        )
        return FilingImportResult(normalized_ticker, year, quarter, file_path.as_posix())


def _parse_date(value: object) -> object:
    """Convert ISO-formatted date-time strings from the SEC client."""
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
