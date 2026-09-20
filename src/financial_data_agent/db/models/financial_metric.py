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

    revenue: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    operating_income: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    net_income: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    total_assets: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    total_liabilities: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    stockholders_equity: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    current_assets: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    operating_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    capital_expenditures: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    free_cash_flow: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    shares_outstanding: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    shares_outstanding_diluted: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    current_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    debt_to_assets_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    period: Mapped[str] = mapped_column(
        String(30),
    )

    year: Mapped[int] = mapped_column(
        nullable=False,
    )

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="financial_metrics",
    )
