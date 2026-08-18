from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: int
    accession_number: str
    document_type: str
    year: int
    quarter: int
    filing_date: date
    period_of_report: date
    raw_document_path: str


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    company_id: int | None = None
    accession_number: str | None = None
    document_type: str | None = None
    year: int | None = None
    quarter: int | None = None
    filing_date: date | None = None
    period_of_report: date | None = None
    raw_document_path: str | None = None


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
