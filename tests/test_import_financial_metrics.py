from __future__ import annotations

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from financial_data_agent.api.main import app
from financial_data_agent.api.v1 import import_financial_metrics
from financial_data_agent.constants import METRIC_FIELDS
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.financial_metric import FinancialMetricRepository
from financial_data_agent.ingestion.financial_metrics import FinancialMetricsFetcher

REQUEST = {"ticker": "aapl", "year": 2026, "quarter": 2}


def make_metrics(**overrides: Decimal | None) -> dict[str, Decimal | None]:
    metrics: dict[str, Decimal | None] = {field: Decimal(index + 1) * 1000 for index, field in enumerate(METRIC_FIELDS)}
    metrics.update(overrides)
    return metrics


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    app.dependency_overrides[import_financial_metrics.get_session] = lambda: db_session
    yield db_session
    app.dependency_overrides.clear()
    db_session.close()


@pytest.fixture
def fetcher_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(FinancialMetricsFetcher, "__init__", lambda self, identity="": None)

    def fake_fetch_metrics(self: FinancialMetricsFetcher, accession_number: str) -> dict[str, Decimal | None]:
        calls.append(accession_number)
        return make_metrics()

    monkeypatch.setattr(FinancialMetricsFetcher, "fetch_metrics", fake_fetch_metrics)
    return calls


def add_company(session: Session) -> int:
    return CompanyRepository(session).create(CompanyDTO(ticker="AAPL", name="Apple Inc.", cik="0000320193")).id


def add_document(session: Session, company_id: int) -> int:
    return (
        DocumentRepository(session)
        .create(
            DocumentDTO(
                company_id=company_id,
                accession_number="0000320193-26-000001",
                document_type="10-Q",
                year=2026,
                quarter=2,
                filing_date=date(2026, 5, 1),
                period_of_report=date(2026, 3, 31),
                raw_document_path="data/AAPL_2026_Q2.md",
            )
        )
        .id
    )


def test_import_financial_metrics_creates_metrics_for_stored_filing(session: Session, fetcher_calls: list[str]) -> None:
    document_id = add_document(session, add_company(session))

    response = TestClient(app).post("/api/v1/financial-metrics/import", json=REQUEST)

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "year": 2026, "quarter": 2, "status": "created"}
    assert fetcher_calls == ["0000320193-26-000001"]
    metric = FinancialMetricRepository(session).get_by_document_id(document_id)
    assert metric is not None
    assert metric.period == "Q2"
    assert metric.year == 2026
    assert metric.revenue == Decimal("1000")
    assert metric.debt_to_assets_ratio == Decimal("14000")


def test_import_financial_metrics_updates_existing_metrics(session: Session, fetcher_calls: list[str]) -> None:
    add_document(session, add_company(session))
    client = TestClient(app)

    first = client.post("/api/v1/financial-metrics/import", json=REQUEST)
    second = client.post("/api/v1/financial-metrics/import", json=REQUEST)

    assert first.json()["status"] == "created"
    assert second.json()["status"] == "updated"
    assert len(FinancialMetricRepository(session).list()) == 1


def test_import_financial_metrics_rejects_missing_company(session: Session, fetcher_calls: list[str]) -> None:
    response = TestClient(app).post("/api/v1/financial-metrics/import", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticker AAPL was not found in the database"
    assert fetcher_calls == []


def test_import_financial_metrics_rejects_missing_filing(session: Session, fetcher_calls: list[str]) -> None:
    add_company(session)

    response = TestClient(app).post("/api/v1/financial-metrics/import", json=REQUEST)

    assert response.status_code == 404
    assert response.json()["detail"] == "Filing for AAPL in 2026 Q2 was not found in the database"
    assert fetcher_calls == []
    assert FinancialMetricRepository(session).list() == []


def test_import_financial_metrics_stores_null_for_unreported_metrics(
    session: Session, monkeypatch: pytest.MonkeyPatch, fetcher_calls: list[str]
) -> None:
    document_id = add_document(session, add_company(session))
    monkeypatch.setattr(
        FinancialMetricsFetcher,
        "fetch_metrics",
        lambda self, accession_number: make_metrics(free_cash_flow=None, current_ratio=None),
    )

    response = TestClient(app).post("/api/v1/financial-metrics/import", json=REQUEST)

    assert response.status_code == 200
    metric = FinancialMetricRepository(session).get_by_document_id(document_id)
    assert metric is not None
    assert metric.free_cash_flow is None
    assert metric.current_ratio is None
    assert metric.revenue == Decimal("1000")


def test_import_financial_metrics_rejects_unavailable_sec_filing(
    session: Session, monkeypatch: pytest.MonkeyPatch, fetcher_calls: list[str]
) -> None:
    add_document(session, add_company(session))

    def fail_fetch_metrics(self: FinancialMetricsFetcher, accession_number: str) -> dict[str, Decimal | None]:
        raise ValueError(f"No SEC filing found for accession number {accession_number}")

    monkeypatch.setattr(FinancialMetricsFetcher, "fetch_metrics", fail_fetch_metrics)

    response = TestClient(app).post("/api/v1/financial-metrics/import", json=REQUEST)

    assert response.status_code == 422
    assert response.json()["detail"] == "No SEC filing found for accession number 0000320193-26-000001"


def test_import_financial_metrics_rejects_invalid_quarter() -> None:
    response = TestClient(app).post(
        "/api/v1/financial-metrics/import", json={"ticker": "AAPL", "year": 2026, "quarter": 5}
    )

    assert response.status_code == 422
