from __future__ import annotations

from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from financial_data_agent.api.main import app
from financial_data_agent.constants import EMBEDDING_DIMENSIONS
from financial_data_agent.db.DTO.document_chunk import DocumentChunkDTO
from financial_data_agent.services import document_chunk_import
from financial_data_agent.services.document_chunk_import import (
    DocumentChunkImportService,
    EmbeddingDimensionError,
    FilingContentNotFoundError,
)
from financial_data_agent.services.filing_import import CompanyNotFoundError
from financial_data_agent.services.financial_metrics_import import DocumentNotFoundError

BLOB_NAME = "ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md"

FILING_MARKDOWN = """# Apple Inc.

## Item 1. Financial Statements

Condensed consolidated statements follow.

| Item | 2026 | 2025 |
|---|---|---|
| Revenue | 90,753 | 81,797 |

## Item 2. MD&A

Revenue increased year over year.
"""


class FakeCompany:
    id = 42
    ticker = "AAPL"


class FakeDocument:
    id = 7
    year = 2026
    quarter = 2


class FakeCompanyRepository:
    def __init__(self, session: object, company: FakeCompany | None = None) -> None:
        self.session = session
        self.company = company

    def get_by_ticker(self, ticker: str) -> FakeCompany | None:
        assert ticker == "AAPL"
        return self.company


class FakeDocumentRepository:
    def __init__(self, session: object, document: FakeDocument | None = None) -> None:
        self.session = session
        self.document = document

    def get_latest_for_period(self, company_id: int, year: int, quarter: int) -> FakeDocument | None:
        assert (company_id, year, quarter) == (42, 2026, 2)
        return self.document


class FakeChunkRepository:
    def __init__(self, session: object, existing: int = 0) -> None:
        self.session = session
        self.existing = existing
        self.created: list[DocumentChunkDTO] = []
        self.deleted_for: list[int] = []

    def count_by_document_id(self, document_id: int) -> int:
        return self.existing

    def delete_by_document_id(self, document_id: int) -> int:
        self.deleted_for.append(document_id)
        return self.existing

    def create_many(self, document_chunk_dtos: Sequence[DocumentChunkDTO]) -> Sequence[object]:
        self.created.extend(document_chunk_dtos)
        return []


class FakeStorage:
    def __init__(self, content: str | None = FILING_MARKDOWN) -> None:
        self.content = content
        self.reads: list[str] = []

    def save_text(self, blob_name: str, content: str) -> str:
        raise AssertionError("the chunk import only reads")

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        raise AssertionError("the chunk import only reads")

    def read_text(self, blob_name: str) -> str:
        self.reads.append(blob_name)
        if self.content is None:
            raise FileNotFoundError(blob_name)
        return self.content


class FakeEmbedder:
    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self.dimensions = dimensions
        self.embedded: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        return [[0.0] * self.dimensions for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimensions


DEFAULT_COMPANY = FakeCompany()
DEFAULT_DOCUMENT = FakeDocument()


@pytest.fixture(autouse=True)
def embedding_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def build_service(
    monkeypatch: pytest.MonkeyPatch,
    chunk_repository: FakeChunkRepository,
    storage: FakeStorage,
    embedder: FakeEmbedder,
    company: FakeCompany | None = DEFAULT_COMPANY,
    document: FakeDocument | None = DEFAULT_DOCUMENT,
) -> DocumentChunkImportService:
    monkeypatch.setattr(
        document_chunk_import, "CompanyRepository", lambda session: FakeCompanyRepository(session, company)
    )
    monkeypatch.setattr(
        document_chunk_import, "DocumentRepository", lambda session: FakeDocumentRepository(session, document)
    )
    monkeypatch.setattr(document_chunk_import, "DocumentChunkRepository", lambda session: chunk_repository)
    return DocumentChunkImportService(session=object(), storage=storage, embedder=embedder)


def test_import_chunks_stores_a_chunk_per_section_with_its_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_repository = FakeChunkRepository(session=object())
    storage = FakeStorage()
    embedder = FakeEmbedder()
    service = build_service(monkeypatch, chunk_repository, storage, embedder)

    result = service.import_chunks(ticker="aapl", year=2026, quarter=2)

    assert result.ticker == "AAPL"
    assert result.status == "created"
    assert result.chunk_count == len(chunk_repository.created)
    assert storage.reads == [BLOB_NAME]
    assert len(embedder.embedded) == len(chunk_repository.created)

    assert [dto.chunk_index for dto in chunk_repository.created] == list(range(len(chunk_repository.created)))
    assert all(dto.document_id == 7 for dto in chunk_repository.created)
    assert all(dto.embedding_model == "BAAI/bge-small-en-v1.5" for dto in chunk_repository.created)
    assert all(len(dto.embedding or []) == EMBEDDING_DIMENSIONS for dto in chunk_repository.created)

    table_chunks = [dto for dto in chunk_repository.created if dto.is_table]
    assert len(table_chunks) == 1
    assert table_chunks[0].heading_path == "Apple Inc. > Item 1. Financial Statements"


def test_import_chunks_reads_the_derived_blob_name_not_the_stored_path(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = FakeStorage()
    service = build_service(monkeypatch, FakeChunkRepository(session=object()), storage, FakeEmbedder())

    service.import_chunks(ticker="AAPL", year=2026, quarter=2)

    assert storage.reads == [BLOB_NAME]


def test_import_chunks_skips_an_already_chunked_document(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_repository = FakeChunkRepository(session=object(), existing=11)
    storage = FakeStorage()
    embedder = FakeEmbedder()
    service = build_service(monkeypatch, chunk_repository, storage, embedder)

    result = service.import_chunks(ticker="AAPL", year=2026, quarter=2)

    assert result.status == "skipped"
    assert result.chunk_count == 11
    assert storage.reads == []
    assert embedder.embedded == []
    assert chunk_repository.created == []


def test_import_chunks_replaces_existing_chunks_when_forced(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_repository = FakeChunkRepository(session=object(), existing=11)
    service = build_service(monkeypatch, chunk_repository, FakeStorage(), FakeEmbedder())

    result = service.import_chunks(ticker="AAPL", year=2026, quarter=2, force=True)

    assert result.status == "replaced"
    assert chunk_repository.deleted_for == [7]
    assert chunk_repository.created


def test_import_chunks_rejects_an_embedder_with_the_wrong_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_repository = FakeChunkRepository(session=object())
    service = build_service(monkeypatch, chunk_repository, FakeStorage(), FakeEmbedder(dimensions=768))

    with pytest.raises(EmbeddingDimensionError, match="768"):
        service.import_chunks(ticker="AAPL", year=2026, quarter=2)

    assert chunk_repository.created == []


def test_import_chunks_raises_when_the_stored_markdown_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = build_service(monkeypatch, FakeChunkRepository(session=object()), FakeStorage(None), FakeEmbedder())

    with pytest.raises(FilingContentNotFoundError, match=BLOB_NAME):
        service.import_chunks(ticker="AAPL", year=2026, quarter=2)


def test_import_chunks_raises_for_an_unknown_company(monkeypatch: pytest.MonkeyPatch) -> None:
    service = build_service(
        monkeypatch, FakeChunkRepository(session=object()), FakeStorage(), FakeEmbedder(), company=None
    )

    with pytest.raises(CompanyNotFoundError, match="AAPL"):
        service.import_chunks(ticker="AAPL", year=2026, quarter=2)


def test_import_chunks_raises_when_the_filing_is_not_in_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    service = build_service(
        monkeypatch, FakeChunkRepository(session=object()), FakeStorage(), FakeEmbedder(), document=None
    )

    with pytest.raises(DocumentNotFoundError, match="2026 Q2"):
        service.import_chunks(ticker="AAPL", year=2026, quarter=2)


def test_import_document_chunks_route_returns_the_import_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_repository = FakeChunkRepository(session=object())
    monkeypatch.setattr(
        document_chunk_import, "CompanyRepository", lambda session: FakeCompanyRepository(session, FakeCompany())
    )
    monkeypatch.setattr(
        document_chunk_import, "DocumentRepository", lambda session: FakeDocumentRepository(session, FakeDocument())
    )
    monkeypatch.setattr(document_chunk_import, "DocumentChunkRepository", lambda session: chunk_repository)
    monkeypatch.setattr(document_chunk_import, "build_data_storage", lambda: FakeStorage())
    monkeypatch.setattr(document_chunk_import, "build_embedder", lambda: FakeEmbedder())

    client = TestClient(app)
    response = client.post("/api/v1/document-chunks/import", json={"ticker": "AAPL", "year": 2026, "quarter": 2})

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "year": 2026,
        "quarter": 2,
        "chunk_count": len(chunk_repository.created),
        "status": "created",
    }


def test_import_document_chunks_route_returns_404_for_an_unknown_company(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        document_chunk_import, "CompanyRepository", lambda session: FakeCompanyRepository(session, None)
    )
    monkeypatch.setattr(document_chunk_import, "build_data_storage", lambda: FakeStorage())
    monkeypatch.setattr(document_chunk_import, "build_embedder", lambda: FakeEmbedder())

    client = TestClient(app)
    response = client.post("/api/v1/document-chunks/import", json={"ticker": "AAPL", "year": 2026, "quarter": 2})

    assert response.status_code == 404
