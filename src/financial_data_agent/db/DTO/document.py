from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from financial_data_agent.db.models.document import Document
from financial_data_agent.db.schemas.document import DocumentCreate, DocumentUpdate


@dataclass(slots=True)
class DocumentDTO:
    company_id: int | None = None
    accession_number: str | None = None
    document_type: str | None = None
    year: int | None = None
    quarter: int | None = None
    filing_date: date | None = None
    period_of_report: date | None = None
    raw_document_path: str | None = None
    supplied_fields: frozenset[str] = frozenset()

    @classmethod
    def from_create_schema(cls, document: DocumentCreate) -> DocumentDTO:
        """Build a DTO from an API create schema.

        Args:
            document: Validated document creation payload.

        Returns:
            A DTO with every field supplied.
        """
        return cls(
            company_id=document.company_id,
            accession_number=document.accession_number,
            document_type=document.document_type,
            year=document.year,
            quarter=document.quarter,
            filing_date=document.filing_date,
            period_of_report=document.period_of_report,
            raw_document_path=document.raw_document_path,
            supplied_fields=frozenset(
                {
                    "company_id",
                    "accession_number",
                    "document_type",
                    "year",
                    "quarter",
                    "filing_date",
                    "period_of_report",
                    "raw_document_path",
                }
            ),
        )

    @classmethod
    def from_update_schema(cls, document: DocumentUpdate) -> DocumentDTO:
        """Build a DTO from an API update schema.

        Args:
            document: Validated document update payload.

        Returns:
            A DTO whose supplied fields are the ones set in the payload.
        """
        supplied_fields = frozenset(document.model_fields_set)
        data = document.model_dump(exclude_unset=True)
        return cls(
            company_id=data.get("company_id"),
            accession_number=data.get("accession_number"),
            document_type=data.get("document_type"),
            year=data.get("year"),
            quarter=data.get("quarter"),
            filing_date=data.get("filing_date"),
            period_of_report=data.get("period_of_report"),
            raw_document_path=data.get("raw_document_path"),
            supplied_fields=supplied_fields,
        )

    def to_model_kwargs(self) -> dict[str, object | None]:
        """Convert the DTO to SQLAlchemy model keyword arguments.

        Returns:
            Keyword arguments for the document model constructor.
        """
        return {
            "company_id": self.company_id,
            "accession_number": self.accession_number,
            "document_type": self.document_type,
            "year": self.year,
            "quarter": self.quarter,
            "filing_date": self.filing_date,
            "period_of_report": self.period_of_report,
            "raw_document_path": self.raw_document_path,
        }

    def apply_to(self, document: Document) -> Document:
        """Apply DTO values to an existing document model.

        Args:
            document: Document model to update.

        Returns:
            The document with the supplied fields applied.
        """
        if "company_id" in self.supplied_fields:
            document.company_id = self.company_id
        if "accession_number" in self.supplied_fields:
            document.accession_number = self.accession_number
        if "document_type" in self.supplied_fields:
            document.document_type = self.document_type
        if "year" in self.supplied_fields:
            document.year = self.year
        if "quarter" in self.supplied_fields:
            document.quarter = self.quarter
        if "filing_date" in self.supplied_fields:
            document.filing_date = self.filing_date
        if "period_of_report" in self.supplied_fields:
            document.period_of_report = self.period_of_report
        if "raw_document_path" in self.supplied_fields:
            document.raw_document_path = self.raw_document_path
        return document
