from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from financial_data_agent.db.models.document import Document


class FinancialMetric(TimestampMixin, Base):
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

    period: Mapped[str | None] = mapped_column(
        String(30),
    )

    year: Mapped[int | None] = mapped_column(
        nullable=False,
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="financial_metrics",
    )
