from __future__ import annotations

from financial_data_agent.api.responses.chat import CitationResponse, FourthQuarterResponse
from financial_data_agent.db.database import get_session_factory
from financial_data_agent.services.filing_import import CompanyNotFoundError, FilingNotFoundError
from financial_data_agent.services.financial_metrics_import import DocumentNotFoundError, MetricsExtractionError
from financial_data_agent.services.fourth_quarter import (
    AnnualFilingNotFoundError,
    FourthQuarterService,
    IncompleteFiscalYearError,
)


def get_fourth_quarter(ticker: str, reporting_year: int, reporting_quarter: int) -> str:
    """Derive a company's fiscal fourth quarter from the 10-K reported in a calendar quarter.

    Use it when a quarter question names a slot that holds only a 10-K and asks for the change from the previous
    quarter or for the isolated quarter. It imports the fiscal year's missing 10-Qs, so it can be slow.

    Args:
        ticker: Ticker symbol of the company.
        reporting_year: Calendar year the 10-K was reported in.
        reporting_quarter: Calendar quarter the 10-K was reported in, from 1 to 4.

    Returns:
        A `FourthQuarterResponse` as JSON, holding single-quarter figures for the fiscal fourth quarter and the
        quarter before it, or the error that stopped the call.
    """
    try:
        with get_session_factory()() as session:
            result = FourthQuarterService(session).derive(ticker, reporting_year, reporting_quarter)
    except (
        CompanyNotFoundError,
        AnnualFilingNotFoundError,
        IncompleteFiscalYearError,
        FilingNotFoundError,
        DocumentNotFoundError,
        MetricsExtractionError,
    ) as error:
        return FourthQuarterResponse(error=str(error)).model_dump_json()
    return FourthQuarterResponse(
        ticker=result.ticker,
        fiscal_year_end=result.fiscal_year_end,
        previous_quarter_end=result.previous_quarter_end,
        fourth_quarter=result.fourth_quarter,
        previous_quarter=result.previous_quarter,
        sources=[CitationResponse.model_validate(source, from_attributes=True) for source in result.sources],
    ).model_dump_json()
