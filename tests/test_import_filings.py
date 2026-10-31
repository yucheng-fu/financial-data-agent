from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from financial_data_agent.api.main import app
from financial_data_agent.db.DTO.document import DOCUMENT_FIELDS, DocumentDTO
from financial_data_agent.ingestion.filings import FetchedFiling
from financial_data_agent.services import filing_import

REQUEST = {"ticker": "AAPL", "reporting_year": 2026, "reporting_quarter": 2}
BLOB_NAME = "ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2_quarterly.md"


class FakeCompany:
    id = 42


class FakeCompanyRepository:
    company: FakeCompany | None = FakeCompany()

    def __init__(self, session: object) -> None:
        self.session = session

    def get_by_ticker(self, ticker: str) -> FakeCompany | None:
        assert ticker == "AAPL"
        return self.company


class FakeDocumentRepository:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.created: list[DocumentDTO] = []
        self.updated: list[tuple[object, DocumentDTO]] = []

    def get_by_accession_number(self, company_id: int, accession_number: str) -> object | None:
        assert (company_id, accession_number) == (42, "0000320193-26-000001")
        return self.existing

    def create(self, document_dto: DocumentDTO) -> object:
        self.created.append(document_dto)
        return object()

    def update(self, document: object, document_dto: DocumentDTO) -> object:
        self.updated.append((document, document_dto))
        return document


def make_fetched_filing() -> FetchedFiling:
    filing = SimpleNamespace(
        accession_number="0000320193-26-000001",
        form="10-Q",
        filing_date="2026-05-01T00:00:00",
        period_of_report="2026-03-31T00:00:00",
    )
    return FetchedFiling(BLOB_NAME, filing, "quarterly")


def patch_services(
    monkeypatch: pytest.MonkeyPatch, document_repository: FakeDocumentRepository, fetched: list[FetchedFiling]
) -> None:
    def fake_fetch_filings(self, ticker: str, form: list[str], quarter: int, year: int) -> list[FetchedFiling]:
        assert (ticker, form, quarter, year) == ("AAPL", ["10-Q", "10-K"], 2, 2026)
        return fetched

    monkeypatch.setattr(filing_import.FilingsFetcher, "fetch_filings", fake_fetch_filings)
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(filing_import, "DocumentRepository", lambda session: document_repository)


def expected_document() -> DocumentDTO:
    return DocumentDTO(
        company_id=42,
        accession_number="0000320193-26-000001",
        document_type="10-Q",
        reporting_year=2026,
        reporting_quarter=2,
        period_type="quarterly",
        filing_date=datetime(2026, 5, 1, 0, 0),
        period_of_report=datetime(2026, 3, 31, 0, 0),
        raw_document_path=BLOB_NAME,
        supplied_fields=frozenset(DOCUMENT_FIELDS),
    )


def test_import_filings_stores_the_reporting_period_and_period_type(monkeypatch) -> None:
    document_repository = FakeDocumentRepository()
    patch_services(monkeypatch, document_repository, [make_fetched_filing()])

    response = TestClient(app).post("/api/v1/filings/import", json=REQUEST)

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "reporting_year": 2026,
        "reporting_quarter": 2,
        "filings": [{"document_type": "10-Q", "period_type": "quarterly", "file_path": BLOB_NAME}],
    }
    assert document_repository.created == [expected_document()]


def test_import_filings_updates_a_filing_that_is_already_stored(monkeypatch) -> None:
    existing = object()
    document_repository = FakeDocumentRepository(existing)
    patch_services(monkeypatch, document_repository, [make_fetched_filing()])

    response = TestClient(app).post("/api/v1/filings/import", json=REQUEST)

    assert response.status_code == 200
    assert document_repository.created == []
    assert document_repository.updated == [(existing, expected_document())]


def test_import_filings_rejects_invalid_quarter() -> None:
    response = TestClient(app).post(
        "/api/v1/filings/import", json={"ticker": "AAPL", "reporting_year": 2026, "reporting_quarter": 5}
    )

    assert response.status_code == 422


def test_import_filings_rejects_missing_company_before_download(monkeypatch) -> None:
    document_repository = FakeDocumentRepository()

    def fail_fetch_filings(self, ticker: str, form: list[str], quarter: int, year: int) -> list[FetchedFiling]:
        raise AssertionError("fetch_filings should not be called when the company is missing")

    monkeypatch.setattr(filing_import.FilingsFetcher, "fetch_filings", fail_fetch_filings)
    monkeypatch.setattr(FakeCompanyRepository, "company", None)
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(filing_import, "DocumentRepository", lambda session: document_repository)

    response = TestClient(app).post("/api/v1/filings/import", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticker AAPL was not found in the database"
    assert document_repository.created == []


def test_import_filings_rejects_missing_sec_filing(monkeypatch) -> None:
    document_repository = FakeDocumentRepository()

    def fake_fetch_filings(self, ticker: str, form: list[str], quarter: int, year: int) -> list[FetchedFiling]:
        raise ValueError("No 10-Q filing found for AAPL in 2026 Q2")

    monkeypatch.setattr(filing_import.FilingsFetcher, "fetch_filings", fake_fetch_filings)
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(filing_import, "DocumentRepository", lambda session: document_repository)

    response = TestClient(app).post("/api/v1/filings/import", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "SEC filing not found for AAPL reported in 2026 Q2"
    assert document_repository.created == []
