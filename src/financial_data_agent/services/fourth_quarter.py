from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from financial_data_agent.constants import (
    CASH_FLOW_FIELDS,
    FISCAL_YEAR_DAYS,
    INCOME_FLOW_FIELDS,
    METRIC_FIELDS,
    POINT_IN_TIME_FIELDS,
    QUARTERS_PER_FISCAL_YEAR,
)
from financial_data_agent.db.models.document import Document
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.financial_metric import FinancialMetricRepository
from financial_data_agent.ingestion.filings import FilingsFetcher
from financial_data_agent.ingestion.financial_metrics import FinancialMetricsFetcher
from financial_data_agent.services.filing_import import CompanyNotFoundError, FilingImportService
from financial_data_agent.services.financial_metrics_import import FinancialMetricsImportService

Metrics = dict[str, Decimal | None]


class AnnualFilingNotFoundError(Exception):
    """Raised when the company has no 10-K stored for the requested reporting period."""


class IncompleteFiscalYearError(Exception):
    """Raised when the three 10-Qs of the fiscal year cannot be found or lack metrics."""


@dataclass(frozen=True, slots=True)
class SourceFiling:
    """A filing a derived figure is based on."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    period_type: str


@dataclass(frozen=True, slots=True)
class FourthQuarterResult:
    """The derived fiscal fourth quarter, the quarter before it and the filings behind them."""

    ticker: str
    fiscal_year_end: date
    previous_quarter_end: date
    fourth_quarter: Metrics
    previous_quarter: Metrics
    sources: list[SourceFiling]


def subtract(minuend: Decimal | None, subtrahends: Sequence[Decimal | None]) -> Decimal | None:
    """Subtract values from a minuend; any missing value makes the result missing.

    Args:
        minuend: The value to subtract from.
        subtrahends: The values to subtract.

    Returns:
        The difference, or None if any input is None.
    """
    result = minuend
    for value in subtrahends:
        if result is None or value is None:
            return None
        result -= value
    return result


def derive_fourth_quarter(
    annual: Mapping[str, Decimal | None], quarters: Sequence[Mapping[str, Decimal | None]]
) -> Metrics:
    """Derive the single-quarter figures of the fiscal fourth quarter.

    Income flows are the 10-K minus the three 10-Qs' quarter values. Cash flows are the 10-K minus the latest
    10-Q's year-to-date value. Point-in-time metrics are the 10-K's. Share counts are not additive and stay empty.

    Args:
        annual: Metrics of the 10-K.
        quarters: Metrics of the three 10-Qs of the fiscal year, oldest first.

    Returns:
        A value for every metric field.
    """
    derived: Metrics = dict.fromkeys(METRIC_FIELDS)
    for field in INCOME_FLOW_FIELDS:
        derived[field] = subtract(annual[field], [quarter[field] for quarter in quarters])
    for field in CASH_FLOW_FIELDS:
        derived[field] = subtract(annual[field], [quarters[-1][field]])
    for field in POINT_IN_TIME_FIELDS:
        derived[field] = annual[field]
    return derived


def isolate_last_quarter(quarters: Sequence[Mapping[str, Decimal | None]]) -> Metrics:
    """Isolate the single-quarter figures of the latest 10-Q.

    Args:
        quarters: Metrics of the three 10-Qs of the fiscal year, oldest first.

    Returns:
        A value for every metric field; cash flows are the year-to-date change from the 10-Q before.
    """
    latest, before = quarters[-1], quarters[-2]
    isolated: Metrics = dict.fromkeys(METRIC_FIELDS)
    for field in (*INCOME_FLOW_FIELDS, *POINT_IN_TIME_FIELDS):
        isolated[field] = latest[field]
    for field in CASH_FLOW_FIELDS:
        isolated[field] = subtract(latest[field], [before[field]])
    return isolated


def preceding_slot(reporting_year: int, reporting_quarter: int, steps: int) -> tuple[int, int]:
    """Step back a number of calendar quarters.

    Args:
        reporting_year: Calendar year of the starting quarter.
        reporting_quarter: Calendar quarter of the starting quarter, from 1 to 4.
        steps: How many quarters to go back.

    Returns:
        The calendar year and quarter reached.
    """
    index = reporting_year * 4 + reporting_quarter - 1 - steps
    return index // 4, index % 4 + 1


class FourthQuarterService:
    """Derive a fiscal fourth quarter from a 10-K and the three 10-Qs of the same fiscal year."""

    def __init__(
        self,
        session: Session,
        filings_fetcher: FilingsFetcher | None = None,
        metrics_fetcher: FinancialMetricsFetcher | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
            filings_fetcher: Optional SEC filing fetcher used to import missing 10-Qs.
            metrics_fetcher: Optional financial metrics fetcher used to import missing 10-Qs.
        """
        self.session = session
        self.filings_fetcher = filings_fetcher
        self.metrics_fetcher = metrics_fetcher
        self.company_repository = CompanyRepository(session)
        self.document_repository = DocumentRepository(session)
        self.metric_repository = FinancialMetricRepository(session)

    def derive(self, ticker: str, reporting_year: int, reporting_quarter: int) -> FourthQuarterResult:
        """Derive the fiscal fourth quarter of the 10-K a company filed in a calendar quarter.

        Missing 10-Qs of the fiscal year are imported from the three calendar quarters before the 10-K's.

        Args:
            ticker: Ticker symbol of the company.
            reporting_year: Calendar year the 10-K was reported in.
            reporting_quarter: Calendar quarter the 10-K was reported in, from 1 to 4.

        Returns:
            The fiscal year end, the derived fourth quarter, the quarter before it and the source filings.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            AnnualFilingNotFoundError: If no 10-K is stored for the period.
            IncompleteFiscalYearError: If the fiscal year does not have exactly three 10-Qs with metrics.
            FilingNotFoundError: If the SEC has no filing for a quarter that has to be imported.
            MetricsExtractionError: If the financial data of an imported filing is unavailable.
        """
        normalized_ticker = ticker.upper()
        company = self.company_repository.get_by_ticker(normalized_ticker)
        if company is None:
            raise CompanyNotFoundError(f"Ticker {normalized_ticker} was not found in the database")
        annual = next(
            (
                document
                for document in self.document_repository.list_by_period(company.id, reporting_year, reporting_quarter)
                if document.period_type == "annual"
            ),
            None,
        )
        if annual is None:
            raise AnnualFilingNotFoundError(
                f"No 10-K of {normalized_ticker} reported in {reporting_year} Q{reporting_quarter} is stored"
            )
        quarterlies = self._quarterlies(company.id, annual)
        if len(quarterlies) < QUARTERS_PER_FISCAL_YEAR:
            self._import_preceding_slots(normalized_ticker, company.id, reporting_year, reporting_quarter)
            quarterlies = self._quarterlies(company.id, annual)
        if len(quarterlies) != QUARTERS_PER_FISCAL_YEAR:
            raise IncompleteFiscalYearError(
                f"Found {len(quarterlies)} 10-Qs of {normalized_ticker} for the fiscal year ended "
                f"{annual.period_of_report}; three are needed"
            )
        annual_metrics = self._metrics(annual)
        quarter_metrics = [self._metrics(document) for document in quarterlies]
        return FourthQuarterResult(
            ticker=normalized_ticker,
            fiscal_year_end=annual.period_of_report,
            previous_quarter_end=quarterlies[-1].period_of_report,
            fourth_quarter=derive_fourth_quarter(annual_metrics, quarter_metrics),
            previous_quarter=isolate_last_quarter(quarter_metrics),
            sources=[
                SourceFiling(
                    normalized_ticker, document.reporting_year, document.reporting_quarter, document.period_type
                )
                for document in (annual, *quarterlies)
            ],
        )

    def _quarterlies(self, company_id: int, annual: Document) -> list[Document]:
        """Return the 10-Qs stored for the fiscal year a 10-K closes.

        Args:
            company_id: Primary key of the company.
            annual: The 10-K.

        Returns:
            The 10-Qs ordered by period end.
        """
        return self.document_repository.list_quarterly_between(
            company_id, annual.period_of_report - timedelta(days=FISCAL_YEAR_DAYS), annual.period_of_report
        )

    def _import_preceding_slots(
        self, ticker: str, company_id: int, reporting_year: int, reporting_quarter: int
    ) -> None:
        """Import the filings of the three calendar quarters before a slot that are not stored yet.

        Args:
            ticker: Ticker symbol of the company.
            company_id: Primary key of the company.
            reporting_year: Calendar year of the 10-K slot.
            reporting_quarter: Calendar quarter of the 10-K slot, from 1 to 4.
        """
        filing_service = FilingImportService(self.session, self.filings_fetcher)
        metrics_service = FinancialMetricsImportService(self.session, self.metrics_fetcher)
        for steps in range(1, QUARTERS_PER_FISCAL_YEAR + 1):
            year, quarter = preceding_slot(reporting_year, reporting_quarter, steps)
            if not self.document_repository.list_by_period(company_id, year, quarter):
                filing_service.import_filings(ticker, year, quarter)
                metrics_service.import_metrics(ticker, year, quarter)

    def _metrics(self, document: Document) -> Metrics:
        """Return the stored metrics of a filing.

        Args:
            document: The filing.

        Returns:
            A value for every metric field.

        Raises:
            IncompleteFiscalYearError: If the filing has no metrics row.
        """
        metric = self.metric_repository.get_by_document_id(document.id)
        if metric is None:
            raise IncompleteFiscalYearError(
                f"The {document.period_type} filing reported in {document.reporting_year} "
                f"Q{document.reporting_quarter} has no metrics stored"
            )
        return {field: getattr(metric, field) for field in METRIC_FIELDS}
