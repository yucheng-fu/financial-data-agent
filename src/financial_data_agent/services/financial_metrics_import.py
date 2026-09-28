from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from financial_data_agent.constants import METRIC_FIELDS
from financial_data_agent.db.DTO.financial_metric import FinancialMetricDTO
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.financial_metric import FinancialMetricRepository
from financial_data_agent.ingestion.financial_metrics import FinancialMetricsFetcher
from financial_data_agent.services.filing_import import CompanyNotFoundError


class DocumentNotFoundError(Exception):
    """Raised when no filing document exists in the database for a requested period."""


class MetricsExtractionError(Exception):
    """Raised when the financial metrics of a filing cannot be extracted."""


@dataclass(frozen=True, slots=True)
class FinancialMetricsImportResult:
    """Outcome of a financial metrics import."""

    ticker: str
    year: int
    quarter: int
    status: str


class FinancialMetricsImportService:
    """Import financial metrics extracted from SEC filings."""

    def __init__(self, session: Session, fetcher: FinancialMetricsFetcher | None = None) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
            fetcher: Optional financial metrics fetcher.
        """
        self.company_repository = CompanyRepository(session)
        self.document_repository = DocumentRepository(session)
        self.metric_repository = FinancialMetricRepository(session)
        self.fetcher = fetcher or FinancialMetricsFetcher()

    def import_metrics(self, ticker: str, year: int, quarter: int) -> FinancialMetricsImportResult:
        """Extract and persist the financial metrics of a stored filing.

        Args:
            ticker: Ticker symbol of the company.
            year: Filing year.
            quarter: Calendar quarter, from 1 to 4.

        Returns:
            The normalized ticker, period, and whether the metrics were created or updated.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            DocumentNotFoundError: If the company has no filing in the database for the period.
            MetricsExtractionError: If the SEC filing or its financial data is unavailable.
        """
        normalized_ticker = ticker.upper()
        company = self.company_repository.get_by_ticker(normalized_ticker)
        if company is None:
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the database")
        document = self.document_repository.get_latest_for_period(company.id, year, quarter)
        if document is None:
            raise DocumentNotFoundError(
                f"Filing for {normalized_ticker} in {year} Q{quarter} was not found in the database"
            )
        try:
            metrics = self.fetcher.fetch_metrics(document.accession_number)
        except ValueError as error:
            raise MetricsExtractionError(str(error)) from error
        metric_dto = FinancialMetricDTO(
            document_id=document.id,
            period=f"Q{document.quarter}",
            year=document.year,
            **{field: metrics.get(field) for field in METRIC_FIELDS},
            supplied_fields=frozenset({"document_id", "period", "year", *METRIC_FIELDS}),
        )
        existing_metric = self.metric_repository.get_by_document_id(document.id)
        if existing_metric is None:
            self.metric_repository.create(metric_dto)
            status = "created"
        else:
            self.metric_repository.update(existing_metric, metric_dto)
            status = "updated"
        return FinancialMetricsImportResult(normalized_ticker, year, quarter, status)
