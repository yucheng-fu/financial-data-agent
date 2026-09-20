from __future__ import annotations

from sqlalchemy.orm import Session


class FinancialMetricsImportService:
    """Import financial metrics extracted from SEC filings."""

    def __init__(self, session: Session) -> None:
        """Initialize the service.

        Args:
            session: Database session used for persistence.
        """
        self.session = session

    def import_metrics(self, ticker: str, year: int, quarter: int) -> None:
        """Import metrics described by the request."""
        del ticker, year, quarter
