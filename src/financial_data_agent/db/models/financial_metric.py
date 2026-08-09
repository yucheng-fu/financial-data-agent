from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base

if TYPE_CHECKING:
    from financial_data_agent.db.models.chunk import Chunk
    from financial_data_agent.db.models.document import Document


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
    )

    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    value: Mapped[Decimal] = mapped_column(
        Numeric(24, 6),
        nullable=False,
    )

    unit: Mapped[str | None] = mapped_column(
        String(30),
    )

    period: Mapped[str | None] = mapped_column(
        String(30),
    )

    period_start: Mapped[str | None] = mapped_column(
        String(30),
    )

    period_end: Mapped[str | None] = mapped_column(
        String(30),
    )

    source_chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"),
    )

    extraction_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="financial_metrics",
    )

    source_chunk: Mapped[Chunk | None] = relationship(
        "Chunk",
    )
