from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.models.company import Company


class CompanyRepository:
    """Repository for CRUD operations on company records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: Database session used for persistence.
        """
        self.session = session

    def create(self, company_dto: CompanyDTO) -> Company:
        """Create and persist a company from a DTO.

        Args:
            company_dto: Company values to persist.

        Returns:
            The persisted company.
        """
        company = Company(**company_dto.to_model_kwargs())
        self.session.add(company)
        self.session.commit()
        self.session.refresh(company)
        return company

    def get_by_id(self, company_id: int) -> Company | None:
        """Return a company by primary key.

        Args:
            company_id: Primary key of the company.

        Returns:
            The company, or None if it does not exist.
        """
        return self.session.get(Company, company_id)

    def get_by_ticker(self, ticker: str) -> Company | None:
        """Return a company by ticker symbol.

        Args:
            ticker: Ticker symbol of the company.

        Returns:
            The company, or None if it does not exist.
        """
        statement = select(Company).where(Company.ticker == ticker)
        return self.session.scalar(statement)

    def get_by_cik(self, cik: str) -> Company | None:
        """Return a company by CIK.

        Args:
            cik: CIK of the company.

        Returns:
            The company, or None if it does not exist.
        """
        statement = select(Company).where(cik == Company.CIK)
        return self.session.scalar(statement)

    def list(self) -> Sequence[Company]:
        """Return all companies ordered by ticker.

        Returns:
            All companies ordered by ticker.
        """
        statement = select(Company).order_by(Company.ticker)
        return self.session.scalars(statement).all()

    def update(
        self,
        company: Company,
        company_dto: CompanyDTO,
    ) -> Company:
        """Update an existing company from a DTO and persist the changes.

        Args:
            company: Company to update.
            company_dto: Values to apply; only supplied fields are written.

        Returns:
            The updated company.
        """
        company_dto.apply_to(company)

        self.session.commit()
        self.session.refresh(company)
        return company

    def delete(self, company: Company) -> None:
        """Delete a company from the database.

        Args:
            company: Company to delete.
        """
        self.session.delete(company)
        self.session.commit()
