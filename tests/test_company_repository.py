from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_company_repository_crud_round_trip() -> None:
    session = make_session()
    repository = CompanyRepository(session)

    company_dto = CompanyDTO(
        ticker="AAPL",
        name="Apple Inc.",
        gics_sector="Information Technology",
        gics_sub_industry="Technology Hardware, Storage & Peripherals",
        date_added=date(2024, 1, 2),
        cik="320193",
    )
    company = repository.create(company_dto)

    assert company.id is not None
    assert repository.get_by_id(company.id) == company
    assert repository.get_by_ticker("AAPL") == company

    companies = repository.list()
    assert len(companies) == 1
    assert companies[0] == company

    updated_company = repository.update(
        company,
        CompanyDTO(
            name="Apple Incorporated",
            gics_sector=None,
            cik=None,
        ),
    )

    assert updated_company.name == "Apple Incorporated"
    assert updated_company.gics_sector is None
    assert updated_company.CIK is None
    assert updated_company.date_added == date(2024, 1, 2)
    assert updated_company.ticker == "AAPL"

    repository.delete(company)

    assert repository.get_by_id(company.id) is None
    assert repository.list() == []
