from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.document_chunk import DocumentChunkDTO
from financial_data_agent.db.models.document_chunk import DocumentChunk


class DocumentChunkRepository:
    """Repository for CRUD operations on document chunk records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: Database session used for persistence.
        """
        self.session = session

    def create(self, document_chunk_dto: DocumentChunkDTO) -> DocumentChunk:
        """Create and persist a document chunk from a DTO.

        Args:
            document_chunk_dto: Document chunk values to persist.

        Returns:
            The persisted document chunk.
        """
        document_chunk = DocumentChunk(**document_chunk_dto.to_model_kwargs())
        self.session.add(document_chunk)
        self.session.commit()
        self.session.refresh(document_chunk)
        return document_chunk

    def create_many(self, document_chunk_dtos: Sequence[DocumentChunkDTO]) -> Sequence[DocumentChunk]:
        """Create and persist several document chunks in a single transaction.

        Args:
            document_chunk_dtos: Document chunk values to persist.

        Returns:
            The persisted document chunks, in the order they were supplied.
        """
        document_chunks = [DocumentChunk(**dto.to_model_kwargs()) for dto in document_chunk_dtos]
        self.session.add_all(document_chunks)
        self.session.commit()
        return document_chunks

    def get_by_id(self, document_chunk_id: int) -> DocumentChunk | None:
        """Return a document chunk by primary key.

        Args:
            document_chunk_id: Primary key of the document chunk.

        Returns:
            The document chunk, or None if it does not exist.
        """
        return self.session.get(DocumentChunk, document_chunk_id)

    def list_by_document_id(self, document_id: int) -> Sequence[DocumentChunk]:
        """Return the chunks of a document ordered by chunk index.

        Args:
            document_id: Primary key of the document.

        Returns:
            The chunks of the document ordered by chunk index.
        """
        statement = (
            select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)
        )
        return self.session.scalars(statement).all()

    def count_by_document_id(self, document_id: int) -> int:
        """Return how many chunks a document has.

        Args:
            document_id: Primary key of the document.

        Returns:
            The number of stored chunks for the document.
        """
        statement = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
        return self.session.scalars(statement).one()

    def delete_by_document_id(self, document_id: int) -> int:
        """Delete every chunk of a document.

        Args:
            document_id: Primary key of the document.

        Returns:
            The number of deleted chunks.
        """
        statement = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        deleted = self.session.execute(statement).rowcount
        self.session.commit()
        return deleted

    def list(self) -> Sequence[DocumentChunk]:
        """Return all document chunks ordered by id.

        Returns:
            All document chunks ordered by id.
        """
        statement = select(DocumentChunk).order_by(DocumentChunk.id)
        return self.session.scalars(statement).all()

    def update(self, document_chunk: DocumentChunk, document_chunk_dto: DocumentChunkDTO) -> DocumentChunk:
        """Update an existing document chunk from a DTO and persist the changes.

        Args:
            document_chunk: Document chunk to update.
            document_chunk_dto: Values to apply; only supplied fields are written.

        Returns:
            The updated document chunk.
        """
        document_chunk_dto.apply_to(document_chunk)
        self.session.commit()
        self.session.refresh(document_chunk)
        return document_chunk

    def delete(self, document_chunk: DocumentChunk) -> None:
        """Delete a document chunk from the database.

        Args:
            document_chunk: Document chunk to delete.
        """
        self.session.delete(document_chunk)
        self.session.commit()
