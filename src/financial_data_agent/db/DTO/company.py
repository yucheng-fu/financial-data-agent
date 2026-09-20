from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from financial_data_agent.db.models.company import Company
from financial_data_agent.db.schemas.company import CompanyCreate, CompanyUpdate


@dataclass(slots=True)
class CompanyDTO:
    ticker: str | None = None
    name: str | None = None
    gics_sector: str | None = None
    gics_sub_industry: str | None = None
    date_added: date | None = None
    cik: str | None = None
    supplied_fields: frozenset[str] = frozenset()

    @classmethod
    def from_create_schema(cls, company: CompanyCreate) -> CompanyDTO:
        """Build a DTO from an API create schema.

        Args:
            company: Validated company creation payload.

        Returns:
            A DTO with every field supplied.
        """
        return cls(
            ticker=company.ticker,
            name=company.name,
            gics_sector=company.gics_sector,
            gics_sub_industry=company.gics_sub_industry,
            date_added=company.date_added,
            cik=company.cik,
            supplied_fields=frozenset({"ticker", "name", "gics_sector", "gics_sub_industry", "date_added", "cik"}),
        )

    @classmethod
    def from_update_schema(cls, company: CompanyUpdate) -> CompanyDTO:
        """Build a DTO from an API update schema.

        Args:
            company: Validated company update payload.

        Returns:
            A DTO whose supplied fields are the ones set in the payload.
        """
        supplied_fields = frozenset(company.model_fields_set)
        data = company.model_dump(exclude_unset=True)
        return cls(
            ticker=data.get("ticker"),
            name=data.get("name"),
            gics_sector=data.get("gics_sector"),
            gics_sub_industry=data.get("gics_sub_industry"),
            date_added=data.get("date_added"),
            cik=data.get("cik"),
            supplied_fields=supplied_fields,
        )

    def to_model_kwargs(self) -> dict[str, object | None]:
        """Convert the DTO to SQLAlchemy model keyword arguments.

        Returns:
            Keyword arguments for the company model constructor.
        """
        return {
            "ticker": self.ticker,
            "name": self.name,
            "gics_sector": self.gics_sector,
            "gics_sub_industry": self.gics_sub_industry,
            "date_added": self.date_added,
            "CIK": self.cik,
        }

    def apply_to(self, company: Company) -> Company:
        """Apply DTO values to an existing company model.

        Args:
            company: Company model to update.

        Returns:
            The company with the supplied fields applied.
        """
        if "ticker" in self.supplied_fields:
            company.ticker = self.ticker
        if "name" in self.supplied_fields:
            company.name = self.name
        if "gics_sector" in self.supplied_fields:
            company.gics_sector = self.gics_sector
        if "gics_sub_industry" in self.supplied_fields:
            company.gics_sub_industry = self.gics_sub_industry
        if "date_added" in self.supplied_fields:
            company.date_added = self.date_added
        if "cik" in self.supplied_fields:
            company.CIK = self.cik
        return company
