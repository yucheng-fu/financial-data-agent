from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base

if TYPE_CHECKING:
    from financial_data_agent.db.models.document import Document


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
    )

    section_title: Mapped[str | None] = mapped_column(
        Text,
    )

    # Must match the dimensionality of your embedding model.
    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="chunks",
    )
