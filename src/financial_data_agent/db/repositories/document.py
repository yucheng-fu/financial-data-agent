from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document import DocumentDTO, FilingCoverage
from financial_data_agent.db.models.company import Company
from financial_data_agent.db.models.document import Document
from financial_data_agent.db.models.document_chunk import DocumentChunk


class DocumentRepository:
    """Repository for CRUD operations on document records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: Database session used for persistence.
        """
        self.session = session

    def create(self, document_dto: DocumentDTO) -> Document:
        """Create and persist a document from a DTO.

        Args:
            document_dto: Document values to persist.

        Returns:
            The persisted document.
        """
        document = Document(**document_dto.to_model_kwargs())
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        """Return a document by primary key.

        Args:
            document_id: Primary key of the document.

        Returns:
            The document, or None if it does not exist.
        """
        return self.session.get(Document, document_id)

    def list_by_period(self, company_id: int, reporting_year: int, reporting_quarter: int) -> list[Document]:
        """Return the documents of a company reported in a calendar quarter.

        A filing stored more than once is returned once, as its most recently created row.

        Args:
            company_id: Primary key of the company.
            reporting_year: Calendar year the filings were reported in.
            reporting_quarter: Calendar quarter the filings were reported in, from 1 to 4.

        Returns:
            The matching documents ordered by id; empty if there are none.
        """
        statement = (
            select(Document)
            .where(
                Document.company_id == company_id,
                Document.reporting_year == reporting_year,
                Document.reporting_quarter == reporting_quarter,
            )
            .order_by(Document.id)
        )
        latest_by_accession = {document.accession_number: document for document in self.session.scalars(statement)}
        return list(latest_by_accession.values())

    def list_coverage(self, ticker: str | None = None) -> list[FilingCoverage]:
        """Return the stored filings with their chunk counts.

        Args:
            ticker: Ticker symbol to restrict the result to, or None for every company.

        Returns:
            One row per company, reporting period and period type, ordered by ticker then period.
        """
        statement = (
            select(
                Company.ticker,
                Document.reporting_year,
                Document.reporting_quarter,
                Document.period_type,
                func.count(DocumentChunk.id),
            )
            .join(Document, Document.company_id == Company.id)
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .group_by(Company.ticker, Document.reporting_year, Document.reporting_quarter, Document.period_type)
            .order_by(Company.ticker, Document.reporting_year, Document.reporting_quarter, Document.period_type)
        )
        if ticker is not None:
            statement = statement.where(Company.ticker == ticker.upper())
        return [FilingCoverage(*row) for row in self.session.execute(statement)]

    def get_by_accession_number(self, company_id: int, accession_number: str) -> Document | None:
        """Return the document of a company for an SEC accession number.

        Args:
            company_id: Primary key of the company.
            accession_number: SEC accession number of the filing.

        Returns:
            The matching document, or None if there is none.
        """
        statement = select(Document).where(
            Document.company_id == company_id, Document.accession_number == accession_number
        )
        return self.session.scalars(statement).first()

    def list(self) -> Sequence[Document]:
        """Return all documents ordered by id.

        Returns:
            All documents ordered by id.
        """
        statement = select(Document).order_by(Document.id)
        return self.session.scalars(statement).all()

    def update(self, document: Document, document_dto: DocumentDTO) -> Document:
        """Update an existing document from a DTO and persist the changes.

        Args:
            document: Document to update.
            document_dto: Values to apply; only supplied fields are written.

        Returns:
            The updated document.
        """
        document_dto.apply_to(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def delete(self, document: Document) -> None:
        """Delete a document from the database.

        Args:
            document: Document to delete.
        """
        self.session.delete(document)
        self.session.commit()
