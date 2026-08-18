from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_data_agent.db.models.company import Company
from financial_data_agent.db.DTO.company import CompanyDTO


class CompanyRepository:
    """Repository for CRUD operations on company records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, company_dto: CompanyDTO) -> Company:
        """Create and persist a company from a DTO."""
        company = Company(**company_dto.to_model_kwargs())
        self.session.add(company)
        self.session.commit()
        self.session.refresh(company)
        return company

    def get_by_id(self, company_id: int) -> Company | None:
        """Return a company by primary key."""
        return self.session.get(Company, company_id)

    def get_by_ticker(self, ticker: str) -> Company | None:
        """Return a company by ticker symbol."""
        statement = select(Company).where(Company.ticker == ticker)
        return self.session.scalar(statement)

    def get_by_cik(self, cik: str) -> Company | None:
        """Return a company by CIK."""
        statement = select(Company).where(Company.CIK == cik)
        return self.session.scalar(statement)

    def list(self) -> Sequence[Company]:
        """Return all companies ordered by ticker."""
        statement = select(Company).order_by(Company.ticker)
        return self.session.scalars(statement).all()

    def update(
        self,
        company: Company,
        company_dto: CompanyDTO,
    ) -> Company:
        """Update an existing company from a DTO and persist the changes."""
        company_dto.apply_to(company)

        self.session.commit()
        self.session.refresh(company)
        return company

    def delete(self, company: Company) -> None:
        """Delete a company from the database."""
        self.session.delete(company)
        self.session.commit()
