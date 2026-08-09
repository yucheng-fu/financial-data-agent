from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base

if TYPE_CHECKING:
    from financial_data_agent.db.models.chunk import Chunk
    from financial_data_agent.db.models.company import Company


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    raw_document_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
    )

    published_at: Mapped[datetime | None]

    company: Mapped[Company] = relationship(
        back_populates="documents",
    )

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document",
    )
