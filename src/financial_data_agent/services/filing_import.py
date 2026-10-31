from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document import DOCUMENT_FIELDS, DocumentDTO
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.ingestion.filings import FetchedFiling, FilingsFetcher


class CompanyNotFoundError(Exception):
    """Raised when a filing is requested for a company not in the database."""


class FilingNotFoundError(Exception):
    """Raised when no SEC filing exists for a requested period."""


@dataclass(frozen=True, slots=True)
class ImportedFiling:
    """A downloaded and persisted filing with its period type."""

    document_type: str
    period_type: str
    file_path: str


@dataclass(frozen=True, slots=True)
class FilingImportResult:
    """Details of the filings reported in a calendar quarter."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    filings: list[ImportedFiling]


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

    def import_filings(self, ticker: str, reporting_year: int, reporting_quarter: int) -> FilingImportResult:
        """Download and persist the filings a company reported in a calendar quarter.

        A filing that is already stored is updated instead of duplicated.

        Args:
            ticker: Ticker symbol of the company.
            reporting_year: Calendar year the filings were reported in.
            reporting_quarter: Calendar quarter the filings were reported in, from 1 to 4.

        Returns:
            The normalized ticker, the reporting period, and the saved filings.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            FilingNotFoundError: If the SEC has no matching filing.
        """
        normalized_ticker = ticker.upper()
        company = self.company_repository.get_by_ticker(normalized_ticker)
        if company is None:
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the database")
        try:
            fetched_filings = self.fetcher.fetch_filings(
                ticker=ticker, form=["10-Q", "10-K"], quarter=reporting_quarter, year=reporting_year
            )
        except ValueError as error:
            raise FilingNotFoundError(
                f"SEC filing not found for {normalized_ticker} reported in {reporting_year} Q{reporting_quarter}"
            ) from error
        for fetched in fetched_filings:
            self._save_document(company.id, fetched, reporting_year, reporting_quarter)
        return FilingImportResult(
            normalized_ticker,
            reporting_year,
            reporting_quarter,
            [ImportedFiling(fetched.filing.form, fetched.period_type, fetched.location) for fetched in fetched_filings],
        )

    def _save_document(
        self, company_id: int, fetched: FetchedFiling, reporting_year: int, reporting_quarter: int
    ) -> None:
        """Create the document of a fetched filing, or update it if the filing is already stored.

        Args:
            company_id: Primary key of the company.
            fetched: The fetched filing.
            reporting_year: Calendar year the filing was reported in.
            reporting_quarter: Calendar quarter the filing was reported in.
        """
        filing = fetched.filing
        document_dto = DocumentDTO(
            company_id=company_id,
            accession_number=filing.accession_number,
            document_type=filing.form,
            reporting_year=reporting_year,
            reporting_quarter=reporting_quarter,
            period_type=fetched.period_type,
            filing_date=_parse_date(filing.filing_date),
            period_of_report=_parse_date(filing.period_of_report),
            raw_document_path=fetched.location,
            supplied_fields=frozenset(DOCUMENT_FIELDS),
        )
        existing = self.document_repository.get_by_accession_number(company_id, filing.accession_number)
        if existing is None:
            self.document_repository.create(document_dto)
        else:
            self.document_repository.update(existing, document_dto)


def _parse_date(value: object) -> object:
    """Convert ISO-formatted date-time strings from the SEC client.

    Args:
        value: ISO-formatted date-time string or an already parsed value.

    Returns:
        The parsed date-time, or the value unchanged if it is not a string.
    """
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
