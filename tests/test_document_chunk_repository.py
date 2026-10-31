from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import Select, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.constants import CHUNK_FIELDS, EMBEDDING_DIMENSIONS
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document import DocumentDTO, FilingCoverage
from financial_data_agent.db.DTO.document_chunk import DocumentChunkDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository
from financial_data_agent.db.repositories.document_chunk import DocumentChunkRepository, build_search_statement

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
            reporting_year=2026,
            reporting_quarter=2,
            period_type="quarterly",
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


def compile_postgres(statement: Select) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def test_build_search_statement_orders_by_cosine_operator_for_hnsw_index() -> None:
    sql = compile_postgres(build_search_statement([0.0] * EMBEDDING_DIMENSIONS, [], [], [], limit=5))

    assert "document_chunks.embedding <=> " in sql
    assert "cosine_distance" not in sql
    assert "WHERE" not in sql


def test_build_search_statement_filters_only_on_supplied_filings() -> None:
    sql = compile_postgres(build_search_statement([0.0] * EMBEDDING_DIMENSIONS, ["AAPL"], [2024], [], limit=5))

    assert "companies.ticker IN" in sql
    assert "documents.reporting_year IN" in sql
    assert "documents.reporting_quarter" not in sql.split("WHERE", 1)[1]
    assert "documents.period_type" not in sql.split("WHERE", 1)[1]


def test_build_search_statement_restricts_a_quarter_filter_to_quarterly_filings() -> None:
    statement = build_search_statement([0.0] * EMBEDDING_DIMENSIONS, ["AAPL"], [2024], [2], limit=5)
    sql = compile_postgres(statement)

    assert "documents.reporting_quarter IN" in sql
    assert "documents.period_type = " in sql
    assert "quarterly" in statement.compile().params.values()


def test_document_repository_list_coverage_counts_chunks_and_filters_by_ticker() -> None:
    session = make_session()
    document_id = make_document_id(session)
    msft = CompanyRepository(session).create(CompanyDTO(ticker="MSFT", name="Microsoft", cik="0000789019"))
    DocumentRepository(session).create(
        DocumentDTO(
            company_id=msft.id,
            accession_number="0000789019-26-000001",
            document_type="10-K",
            reporting_year=2026,
            reporting_quarter=3,
            period_type="annual",
            filing_date=date(2026, 8, 1),
            period_of_report=date(2026, 6, 30),
            raw_document_path="MSFT_2026_Q3.md",
        )
    )
    DocumentChunkRepository(session).create_many([make_chunk_dto(document_id, 0), make_chunk_dto(document_id, 1)])
    repository = DocumentRepository(session)

    assert repository.list_coverage() == [
        FilingCoverage("AAPL", 2026, 2, "quarterly", 2),
        FilingCoverage("MSFT", 2026, 3, "annual", 0),
    ]
    assert repository.list_coverage("msft") == [FilingCoverage("MSFT", 2026, 3, "annual", 0)]
