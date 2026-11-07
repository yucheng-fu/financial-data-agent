from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from financial_data_agent.api.tools import acquire_filing as acquire_module
from financial_data_agent.api.tools.acquire_filing import FilingAcquirer
from financial_data_agent.services.document_chunk_import import (
    DocumentChunkImportResult,
    FilingContentNotFoundError,
    ImportedChunks,
)
from financial_data_agent.services.filing_import import CompanyNotFoundError, FilingNotFoundError

CHUNKS = DocumentChunkImportResult("AAPL", 2024, 3, [ImportedChunks("10-Q", "quarterly", 40, "created")])


class FakeService:
    """Stands in for each import service, recording which of them ran."""

    calls: list[str] = []
    error: Exception | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def import_filings(self, *args: Any) -> None:
        self.calls.append("filing")
        if self.error:
            raise self.error

    def import_metrics(self, *args: Any) -> None:
        self.calls.append("metrics")

    def import_chunks(self, *args: Any) -> DocumentChunkImportResult:
        self.calls.append("chunks")
        if self.error:
            raise self.error
        return CHUNKS


def use_fakes(
    monkeypatch: pytest.MonkeyPatch, stored: bool = False, known_company: bool = True, error: Exception | None = None
) -> list[str]:
    calls: list[str] = []
    service = type("Service", (FakeService,), {"calls": calls, "error": error})
    documents = MagicMock()
    documents.return_value.list_by_period.return_value = [object()] if stored else []
    companies = MagicMock()
    companies.return_value.get_by_ticker.return_value = SimpleNamespace(id=1) if known_company else None
    monkeypatch.setattr(acquire_module, "get_session_factory", lambda: MagicMock())
    monkeypatch.setattr(acquire_module, "get_embedder", lambda: MagicMock())
    monkeypatch.setattr(acquire_module, "CompanyRepository", companies)
    monkeypatch.setattr(acquire_module, "DocumentRepository", documents)
    monkeypatch.setattr(acquire_module, "FilingImportService", service)
    monkeypatch.setattr(acquire_module, "FinancialMetricsImportService", service)
    monkeypatch.setattr(acquire_module, "DocumentChunkImportService", service)
    return calls


def test_acquire_filing_imports_filing_metrics_and_chunks_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = use_fakes(monkeypatch)

    result = json.loads(FilingAcquirer().acquire_filing("aapl", 2024, 3))

    assert calls == ["filing", "metrics", "chunks"]
    assert result["result"]["filings"] == [
        {"document_type": "10-Q", "period_type": "quarterly", "chunk_count": 40, "status": "created"}
    ]
    assert result["error"] is None


def test_acquire_filing_only_chunks_a_filing_that_is_already_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = use_fakes(monkeypatch, stored=True)

    FilingAcquirer().acquire_filing("AAPL", 2024, 3)

    assert calls == ["chunks"]


def test_acquire_filing_refuses_once_the_budget_is_spent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = use_fakes(monkeypatch)
    acquirer = FilingAcquirer(max_acquisitions=1)

    acquirer.acquire_filing("AAPL", 2024, 3)
    refused = json.loads(acquirer.acquire_filing("AAPL", 2024, 2))

    assert refused["error"].startswith("Acquisition budget spent")
    assert calls == ["filing", "metrics", "chunks"]


def test_acquire_filing_reports_unknown_company_as_error_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = use_fakes(monkeypatch, known_company=False)

    result = json.loads(FilingAcquirer().acquire_filing("zzzz", 2024, 3))

    assert result["error"] == "Ticker ZZZZ was not found in the database"
    assert calls == []


@pytest.mark.parametrize(
    "error",
    [FilingNotFoundError("no filing"), CompanyNotFoundError("no company"), FilingContentNotFoundError("blob gone")],
)
def test_acquire_filing_reports_service_errors_as_error_text(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    use_fakes(monkeypatch, error=error)

    assert json.loads(FilingAcquirer().acquire_filing("AAPL", 2024, 3))["error"] == str(error)
