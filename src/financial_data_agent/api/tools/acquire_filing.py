from __future__ import annotations

from sqlalchemy.orm import Session

from financial_data_agent.api.responses.chat import AcquireFilingResponse
from financial_data_agent.api.responses.document_chunks import DocumentChunkImportResponse, ImportedChunksResponse
from financial_data_agent.constants import CHAT_ACQUISITION_LIMIT
from financial_data_agent.db.database import get_session_factory
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.ingestion.embeddings import get_embedder
from financial_data_agent.services.document_chunk_import import (
    DocumentChunkImportService,
    EmbeddingDimensionError,
    FilingContentNotFoundError,
)
from financial_data_agent.services.filing_import import CompanyNotFoundError, FilingImportService, FilingNotFoundError
from financial_data_agent.services.financial_metrics_import import (
    DocumentNotFoundError,
    FinancialMetricsImportService,
    MetricsExtractionError,
)


class FilingAcquirer:
    """The acquire_filing tool with a budget that lasts as long as the instance, i.e. one chat request."""

    def __init__(self, max_acquisitions: int = CHAT_ACQUISITION_LIMIT) -> None:
        """Initialize the acquirer.

        Args:
            max_acquisitions: How many times the tool may run before it refuses.
        """
        self.max_acquisitions = max_acquisitions
        self.used = 0

    def acquire_filing(self, ticker: str, reporting_year: int, reporting_quarter: int) -> str:
        """Download a missing SEC filing, extract its metrics and make its text searchable.

        Call it only when a result says the filing is missing, and at most once per period. It is slow and has
        a small request budget.

        Args:
            ticker: Ticker symbol of the company.
            reporting_year: Calendar year the filing was reported in.
            reporting_quarter: Calendar quarter the filing was reported in, from 1 to 4.

        Returns:
            An `AcquireFilingResponse` as JSON, holding each stored filing with its chunk count, or the error
            that stopped the call.
        """
        if self.used >= self.max_acquisitions:
            return AcquireFilingResponse(
                error="Acquisition budget spent; answer with the data available"
            ).model_dump_json()
        self.used += 1
        try:
            with get_session_factory()() as session:
                result = self._acquire(session, ticker, reporting_year, reporting_quarter)
        except (
            CompanyNotFoundError,
            FilingNotFoundError,
            DocumentNotFoundError,
            MetricsExtractionError,
            FilingContentNotFoundError,
            EmbeddingDimensionError,
        ) as error:
            return AcquireFilingResponse(error=str(error)).model_dump_json()
        return AcquireFilingResponse(result=result).model_dump_json()

    def _acquire(
        self, session: Session, ticker: str, reporting_year: int, reporting_quarter: int
    ) -> DocumentChunkImportResponse:
        """Import whatever the filing of a period is missing, in order: document, metrics, chunks.

        Args:
            session: Database session used for persistence.
            ticker: Ticker symbol of the company.
            reporting_year: Calendar year the filing was reported in.
            reporting_quarter: Calendar quarter the filing was reported in, from 1 to 4.

        Returns:
            The ticker, the period and each filing with its chunk count.

        Raises:
            CompanyNotFoundError: If the company does not exist in the database.
            FilingNotFoundError: If the SEC has no matching filing.
            MetricsExtractionError: If the financial data of the filing is unavailable.
            FilingContentNotFoundError: If the stored markdown of a filing is missing.
            EmbeddingDimensionError: If the embedder returns vectors of the wrong dimension.
        """
        company = CompanyRepository(session).get_by_ticker(ticker.upper())
        if company is None:
            raise CompanyNotFoundError(f"Ticker {ticker.upper()} was not found in the database")
        if not DocumentRepository(session).list_by_period(company.id, reporting_year, reporting_quarter):
            FilingImportService(session).import_filings(ticker, reporting_year, reporting_quarter)
            FinancialMetricsImportService(session).import_metrics(ticker, reporting_year, reporting_quarter)
        chunks = DocumentChunkImportService(session, embedder=get_embedder()).import_chunks(
            ticker, reporting_year, reporting_quarter
        )
        return DocumentChunkImportResponse(
            ticker=chunks.ticker,
            reporting_year=chunks.reporting_year,
            reporting_quarter=chunks.reporting_quarter,
            filings=[
                ImportedChunksResponse(
                    document_type=item.document_type,
                    period_type=item.period_type,
                    chunk_count=item.chunk_count,
                    status=item.status,
                )
                for item in chunks.filings
            ],
        )
