from __future__ import annotations

from dataclasses import dataclass

from financial_data_agent.constants import CHUNK_FIELDS
from financial_data_agent.db.models.document_chunk import DocumentChunk


@dataclass(slots=True)
class DocumentChunkDTO:
    document_id: int | None = None
    chunk_index: int | None = None
    content: str | None = None
    is_table: bool | None = None
    heading_path: str | None = None
    token_count: int | None = None
    embedding_model: str | None = None
    embedding: list[float] | None = None
    supplied_fields: frozenset[str] = frozenset()

    def to_model_kwargs(self) -> dict[str, object | None]:
        """Convert the DTO to SQLAlchemy model keyword arguments.

        Returns:
            Keyword arguments for the document chunk model constructor.
        """
        return {field: getattr(self, field) for field in CHUNK_FIELDS}

    def apply_to(self, document_chunk: DocumentChunk) -> DocumentChunk:
        """Apply DTO values to an existing document chunk model.

        Args:
            document_chunk: Document chunk model to update.

        Returns:
            The document chunk with the supplied fields applied.
        """
        for field in CHUNK_FIELDS:
            if field in self.supplied_fields:
                setattr(document_chunk, field, getattr(self, field))
        return document_chunk
