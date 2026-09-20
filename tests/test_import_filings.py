from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from financial_data_agent.api.main import app
from financial_data_agent.api.v1 import import_filings
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.services import filing_import


def test_import_filings_downloads_filing(monkeypatch) -> None:
    class FakeCompany:
        id = 42

    class FakeCompanyRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        def get_by_ticker(self, ticker: str) -> FakeCompany | None:
            assert ticker == "AAPL"
            return FakeCompany()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            self.session = session
            self.created_document: DocumentDTO | None = None

        def create(self, document_dto: DocumentDTO) -> object:
            self.created_document = document_dto
            return object()

    fake_document_repository = FakeDocumentRepository(session=object())

    def fake_fetch_filing(self, ticker: str, form: list[str], quarter: int, year: int) -> tuple[Path, object]:
        assert ticker == "AAPL"
        assert form == ["10-Q", "10-K"]
        assert quarter == 2
        assert year == 2026
        filing = SimpleNamespace(
            accession_number="0000320193-26-000001",
            form="10-Q",
            filing_date="2026-05-01T00:00:00",
            period_of_report="2026-03-31T00:00:00",
        )
        return Path("data/ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md"), filing

    monkeypatch.setattr(
        filing_import.FilingsFetcher,
        "fetch_filing",
        fake_fetch_filing,
    )
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(
        filing_import,
        "DocumentRepository",
        lambda session: fake_document_repository,
    )

    app.dependency_overrides[import_filings.get_session] = lambda: object()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/filings/import",
            json={"ticker": "AAPL", "year": 2026, "quarter": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "year": 2026,
        "quarter": 2,
        "file_path": "data/ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md",
    }
    assert fake_document_repository.created_document == DocumentDTO(
        company_id=42,
        accession_number="0000320193-26-000001",
        document_type="10-Q",
        year=2026,
        quarter=2,
        filing_date=datetime(2026, 5, 1, 0, 0),
        period_of_report=datetime(2026, 3, 31, 0, 0),
        raw_document_path="data/ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md",
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


def test_import_filings_rejects_invalid_quarter() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/filings/import",
        json={"ticker": "AAPL", "year": 2026, "quarter": 5},
    )

    assert response.status_code == 422


def test_import_filings_rejects_missing_company_before_download(monkeypatch) -> None:
    class FakeCompanyRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        def get_by_ticker(self, ticker: str) -> None:
            assert ticker == "AAPL"
            return None

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            self.session = session
            self.create_called = False

        def create(self, document_dto: DocumentDTO) -> object:
            self.create_called = True
            return object()

    def fail_fetch_filing(self, ticker: str, form: list[str], quarter: int, year: int) -> Path:
        raise AssertionError("fetch_filing should not be called when the company is missing")

    fake_document_repository = FakeDocumentRepository(session=object())
    monkeypatch.setattr(filing_import.FilingsFetcher, "fetch_filing", fail_fetch_filing)
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(
        filing_import,
        "DocumentRepository",
        lambda session: fake_document_repository,
    )

    app.dependency_overrides[import_filings.get_session] = lambda: object()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/filings/import",
            json={"ticker": "AAPL", "year": 2026, "quarter": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticker AAPL was not found in the database"
    assert fake_document_repository.create_called is False


def test_import_filings_rejects_missing_sec_filing(monkeypatch) -> None:
    class FakeCompany:
        id = 42

    class FakeCompanyRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        def get_by_ticker(self, ticker: str) -> FakeCompany | None:
            assert ticker == "AAPL"
            return FakeCompany()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            self.session = session
            self.create_called = False

        def create(self, document_dto: DocumentDTO) -> object:
            self.create_called = True
            return object()

    def fake_fetch_filing(self, ticker: str, form: list[str], quarter: int, year: int) -> Path:
        raise ValueError("No 10-Q filing found for AAPL in 2026 Q2")

    fake_document_repository = FakeDocumentRepository(session=object())
    monkeypatch.setattr(filing_import.FilingsFetcher, "fetch_filing", fake_fetch_filing)
    monkeypatch.setattr(filing_import, "CompanyRepository", FakeCompanyRepository)
    monkeypatch.setattr(
        filing_import,
        "DocumentRepository",
        lambda session: fake_document_repository,
    )

    app.dependency_overrides[import_filings.get_session] = lambda: object()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/filings/import",
            json={"ticker": "AAPL", "year": 2026, "quarter": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "SEC filing not found for AAPL in 2026 Q2"
    assert fake_document_repository.create_called is False
