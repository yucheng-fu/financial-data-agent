from __future__ import annotations

from decimal import Decimal

from edgar import find, set_identity

from financial_data_agent.constants import SEC_IDENTITY

EDGAR_METRIC_KEYS: dict[str, str] = {
    "revenue": "revenue",
    "operating_income": "operating_income",
    "net_income": "net_income",
    "total_assets": "total_assets",
    "total_liabilities": "total_liabilities",
    "stockholders_equity": "stockholders_equity",
    "current_assets": "current_assets",
    "operating_cash_flow": "operating_cash_flow",
    "capital_expenditures": "capital_expenditures",
    "free_cash_flow": "free_cash_flow",
    "shares_outstanding": "shares_outstanding_basic",
    "shares_outstanding_diluted": "shares_outstanding_diluted",
    "current_ratio": "current_ratio",
    "debt_to_assets_ratio": "debt_to_assets",
}


class FinancialMetricsFetcher:
    """Extract financial metrics from SEC filings."""

    def __init__(self, identity: str = SEC_IDENTITY) -> None:
        """Initialize the fetcher.

        Args:
            identity: SEC fair access identity string.
        """
        set_identity(identity)

    def fetch_metrics(self, accession_number: str) -> dict[str, Decimal | None]:
        """Extract the financial metrics of a filing.

        Args:
            accession_number: SEC accession number of the filing.

        Returns:
            Metric values keyed by database field name; metrics the filing does not report are None.

        Raises:
            ValueError: If the filing or its financial data cannot be found.
        """
        filing = find(accession_number)
        if filing is None:
            raise ValueError(f"No SEC filing found for accession number {accession_number}")
        financials = filing.obj().financials
        if financials is None:
            raise ValueError(f"No financial data found in filing {accession_number}")
        raw_metrics = financials.get_financial_metrics()
        return {
            field: None if raw_metrics.get(key) is None else Decimal(str(raw_metrics[key]))
            for field, key in EDGAR_METRIC_KEYS.items()
        }
