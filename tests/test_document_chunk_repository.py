from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.constants import CHUNK_FIELDS, EMBEDDING_DIMENSIONS
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.DTO.document_chunk import DocumentChunkDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.document_chunk import DocumentChunkRepository

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def make_document_id(session: Session) -> int:
    company = CompanyRepository(session).create(CompanyDTO(ticker="AAPL", name="Apple Inc.", cik="0000320193"))
    document = DocumentRepository(session).create(
        DocumentDTO(
            company_id=company.id,
            accession_number="0000320193-26-000001",
            document_type="10-Q",
            year=2026,
            quarter=2,
            filing_date=date(2026, 5, 1),
            period_of_report=date(2026, 3, 31),
            raw_document_path="data/ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md",
        )
    )
    return document.id


def make_chunk_dto(document_id: int, chunk_index: int, is_table: bool = False) -> DocumentChunkDTO:
    return DocumentChunkDTO(
        document_id=document_id,
        chunk_index=chunk_index,
        content=f"chunk {chunk_index}",
        is_table=is_table,
        heading_path="Item 2. MD&A > Results of Operations",
        token_count=12,
        embedding_model=EMBEDDING_MODEL,
        embedding=[0.0] * EMBEDDING_DIMENSIONS,
        supplied_fields=frozenset(CHUNK_FIELDS),
    )


def test_document_chunk_repository_crud_round_trip() -> None:
    session = make_session()
    document_id = make_document_id(session)
    repository = DocumentChunkRepository(session)

    chunk = repository.create(make_chunk_dto(document_id, 0))

    assert chunk.id is not None
    assert repository.get_by_id(chunk.id) == chunk
    assert repository.get_by_id(chunk.id + 1) is None
    assert repository.list() == [chunk]

    updated_chunk = repository.update(
        chunk,
        DocumentChunkDTO(content="revised", is_table=True, supplied_fields=frozenset({"content", "is_table"})),
    )

    assert updated_chunk.content == "revised"
    assert updated_chunk.is_table is True
    assert updated_chunk.chunk_index == 0
    assert updated_chunk.embedding_model == EMBEDDING_MODEL

    repository.delete(chunk)

    assert repository.get_by_id(chunk.id) is None
    assert repository.list() == []


def test_create_many_persists_every_chunk_in_order() -> None:
    session = make_session()
    document_id = make_document_id(session)
    repository = DocumentChunkRepository(session)

    repository.create_many([make_chunk_dto(document_id, index) for index in range(3)])

    stored = repository.list_by_document_id(document_id)
    assert [chunk.chunk_index for chunk in stored] == [0, 1, 2]
    assert [chunk.content for chunk in stored] == ["chunk 0", "chunk 1", "chunk 2"]
    assert repository.count_by_document_id(document_id) == 3


def test_count_by_document_id_is_zero_for_an_unchunked_document() -> None:
    session = make_session()
    document_id = make_document_id(session)

    assert DocumentChunkRepository(session).count_by_document_id(document_id) == 0


def test_delete_by_document_id_removes_every_chunk_and_reports_the_count() -> None:
    session = make_session()
    document_id = make_document_id(session)
    repository = DocumentChunkRepository(session)
    repository.create_many([make_chunk_dto(document_id, index) for index in range(3)])

    deleted = repository.delete_by_document_id(document_id)

    assert deleted == 3
    assert repository.count_by_document_id(document_id) == 0


def test_document_chunk_repository_rejects_a_duplicate_chunk_index() -> None:
    session = make_session()
    document_id = make_document_id(session)
    repository = DocumentChunkRepository(session)
    repository.create(make_chunk_dto(document_id, 0))

    with pytest.raises(IntegrityError):
        repository.create(make_chunk_dto(document_id, 0))


def test_document_chunk_repository_update_ignores_unsupplied_fields() -> None:
    session = make_session()
    document_id = make_document_id(session)
    repository = DocumentChunkRepository(session)
    chunk = repository.create(make_chunk_dto(document_id, 0))

    updated_chunk = repository.update(chunk, DocumentChunkDTO(content="ignored", token_count=999))

    assert updated_chunk.content == "chunk 0"
    assert updated_chunk.token_count == 12
