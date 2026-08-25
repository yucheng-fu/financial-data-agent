from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from financial_data_agent.api.requests.filings import FilingImportRequest
from financial_data_agent.api.responses.filings import FilingImportResponse
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.database import get_session
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.ingestion.filings import FilingsFetcher

router = APIRouter(tags=["Import filings"])


def import_filing(
    request: FilingImportRequest,
    session: Session,
) -> FilingImportResponse:
    """Download a SEC 10-Q (quarter report) or 10-K (annual report) filing for the requested ticker and period."""
    company_repository = CompanyRepository(session)
    company = company_repository.get_by_ticker(request.ticker.upper())
    if company is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker {request.ticker.upper()} was not found in the database",
        )

    try:
        fetcher = FilingsFetcher()
        file_path, filing = fetcher.fetch_filing(
            ticker=request.ticker,
            form=["10-Q", "10-K"],
            quarter=request.quarter,
            year=request.year,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "SEC filing not found for "
                f"{request.ticker.upper()} in {request.year} Q{request.quarter}"
            ),
        ) from error

    document_repository = DocumentRepository(session)
    document_repository.create(
        DocumentDTO(
            company_id=company.id,
            accession_number=filing.accession_number,
            document_type=filing.form,
            year=request.year,
            quarter=request.quarter,
            filing_date=filing.filing_date,
            period_of_report=filing.period_of_report,
            raw_document_path=str(file_path),
            supplied_fields=frozenset(
                {
                    "company_id",
                    "accession_number",
                    "document_type",
                    "year",
                    "quarter",
                    "filing_date",
                    "period_of_report",
                    "raw_document_path",
                }
            ),
        )
    )

    return FilingImportResponse(
        ticker=request.ticker.upper(),
        year=request.year,
        quarter=request.quarter,
        file_path=str(file_path),
    )


@router.post("/filings/import", summary="Download a SEC 10-Q filing")
def download_filing(
    request: FilingImportRequest,
    session: Session = Depends(get_session),
) -> FilingImportResponse:
    """Download a SEC filing for the requested ticker, year, and quarter."""
    return import_filing(request, session)
