from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.db.repositories.document import DocumentRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def make_company_id(session: Session) -> int:
    company = CompanyRepository(session).create(CompanyDTO(ticker="AAPL", name="Apple Inc.", cik="0000320193"))
    return company.id


def test_document_repository_crud_round_trip() -> None:
    session = make_session()
    company_id = make_company_id(session)
    repository = DocumentRepository(session)

    document_dto = DocumentDTO(
        company_id=company_id,
        accession_number="0000320193-26-000001",
        document_type="10-Q",
        year=2026,
        quarter=2,
        filing_date=date(2026, 5, 1),
        period_of_report=date(2026, 3, 31),
        raw_document_path="data/ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2.md",
    )
    document = repository.create(document_dto)

    # Verify that the document was created and can be retrieved by ID
    assert document.id is not None
    assert repository.get_by_id(document.id) == document
    assert repository.get_by_id(document.id + 1) is None

    documents = repository.list()
    assert len(documents) == 1
    assert documents[0] == document

    # Update only the supplied fields
    updated_document = repository.update(
        document,
        DocumentDTO(
            document_type="10-K",
            quarter=4,
            raw_document_path="data/ticker=AAPL/year=2026/quarter=Q4/AAPL_2026_Q4.md",
            supplied_fields=frozenset({"document_type", "quarter", "raw_document_path"}),
        ),
    )

    # Verify that the supplied fields changed and the others were left untouched
    assert updated_document.document_type == "10-K"
    assert updated_document.quarter == 4
    assert updated_document.raw_document_path == "data/ticker=AAPL/year=2026/quarter=Q4/AAPL_2026_Q4.md"
    assert updated_document.company_id == company_id
    assert updated_document.accession_number == "0000320193-26-000001"
    assert updated_document.year == 2026
    assert updated_document.filing_date == date(2026, 5, 1)
    assert updated_document.period_of_report == date(2026, 3, 31)

    # Delete the document
    repository.delete(document)

    # Verify that the document was deleted
    assert repository.get_by_id(document.id) is None
    assert repository.list() == []


def test_document_repository_update_ignores_unsupplied_fields() -> None:
    session = make_session()
    company_id = make_company_id(session)
    repository = DocumentRepository(session)
    document = repository.create(
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

    updated_document = repository.update(document, DocumentDTO(document_type="10-K", year=2025))

    assert updated_document.document_type == "10-Q"
    assert updated_document.year == 2026


def test_document_repository_create_rejects_missing_required_fields() -> None:
    session = make_session()
    company_id = make_company_id(session)
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError):
        repository.create(DocumentDTO(company_id=company_id, accession_number="0000320193-26-000001"))
