from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    name: str
    gics_sector: str | None = None
    gics_sub_industry: str | None = None
    date_added: date | None = None
    cik: str | None = Field(default=None, alias="CIK")


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str | None = None
    name: str | None = None
    gics_sector: str | None = None
    gics_sub_industry: str | None = None
    date_added: date | None = None
    cik: str | None = Field(default=None, alias="CIK")


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
