from __future__ import annotations

from financial_data_agent.api.responses.chat import FilingCoverageResponse, ListAvailableFilingsResponse
from financial_data_agent.db.database import get_session_factory
from financial_data_agent.db.repositories.document import DocumentRepository


def list_available_filings(ticker: str | None = None) -> str:
    """List the filings stored in the database with the number of searchable text chunks each has.

    Args:
        ticker: Ticker symbol to restrict the list to, or null for every company.

    Returns:
        A `ListAvailableFilingsResponse` as JSON, one entry per ticker, reporting year, reporting quarter and
        period type.
    """
    with get_session_factory()() as session:
        coverage = DocumentRepository(session).list_coverage(ticker)
    return ListAvailableFilingsResponse(
        filings=[FilingCoverageResponse.model_validate(item, from_attributes=True) for item in coverage]
    ).model_dump_json()
