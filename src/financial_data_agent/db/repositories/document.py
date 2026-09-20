from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document import DocumentDTO
from financial_data_agent.db.models.document import Document


class DocumentRepository:
    """Repository for CRUD operations on document records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, document_dto: DocumentDTO) -> Document:
        """Create and persist a document from a DTO."""
        document = Document(**document_dto.to_model_kwargs())
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        """Return a document by primary key."""
        return self.session.get(Document, document_id)

    def get_latest_for_period(self, company_id: int, year: int, quarter: int) -> Document | None:
        """Return the most recently created document of a company for a period."""
        statement = (
            select(Document)
            .where(Document.company_id == company_id, Document.year == year, Document.quarter == quarter)
            .order_by(Document.id.desc())
        )
        return self.session.scalars(statement).first()

    def list(self) -> Sequence[Document]:
        """Return all documents ordered by id."""
        statement = select(Document).order_by(Document.id)
        return self.session.scalars(statement).all()

    def update(self, document: Document, document_dto: DocumentDTO) -> Document:
        """Update an existing document from a DTO and persist the changes."""
        document_dto.apply_to(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def delete(self, document: Document) -> None:
        """Delete a document from the database."""
        self.session.delete(document)
        self.session.commit()
