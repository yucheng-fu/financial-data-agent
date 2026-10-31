from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from financial_data_agent.db.models.document import Document
from financial_data_agent.db.schemas.document import DocumentCreate, DocumentUpdate

DOCUMENT_FIELDS: tuple[str, ...] = (
    "company_id",
    "accession_number",
    "document_type",
    "reporting_year",
    "reporting_quarter",
    "period_type",
    "filing_date",
    "period_of_report",
    "raw_document_path",
)


@dataclass(slots=True)
class DocumentDTO:
    company_id: int | None = None
    accession_number: str | None = None
    document_type: str | None = None
    reporting_year: int | None = None
    reporting_quarter: int | None = None
    period_type: str | None = None
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
            **{field: getattr(document, field) for field in DOCUMENT_FIELDS},
            supplied_fields=frozenset(DOCUMENT_FIELDS),
        )

    @classmethod
    def from_update_schema(cls, document: DocumentUpdate) -> DocumentDTO:
        """Build a DTO from an API update schema.

        Args:
            document: Validated document update payload.

        Returns:
            A DTO whose supplied fields are the ones set in the payload.
        """
        data = document.model_dump(exclude_unset=True)
        return cls(
            **{field: data.get(field) for field in DOCUMENT_FIELDS},
            supplied_fields=frozenset(document.model_fields_set),
        )

    def to_model_kwargs(self) -> dict[str, object | None]:
        """Convert the DTO to SQLAlchemy model keyword arguments.

        Returns:
            Keyword arguments for the document model constructor.
        """
        return {field: getattr(self, field) for field in DOCUMENT_FIELDS}

    def apply_to(self, document: Document) -> Document:
        """Apply DTO values to an existing document model.

        Args:
            document: Document model to update.

        Returns:
            The document with the supplied fields applied.
        """
        for field in DOCUMENT_FIELDS:
            if field in self.supplied_fields:
                setattr(document, field, getattr(self, field))
        return document


@dataclass(frozen=True, slots=True)
class FilingCoverage:
    """A stored filing and how many chunks it has."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    period_type: str
    chunk_count: int
