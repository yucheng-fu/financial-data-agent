from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, BigInteger
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

    revenue: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    operating_income: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    net_income: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    total_assets: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    total_liabilities: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    stockholders_equity: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    current_assets: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    operating_cash_flow: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    capital_expenditures: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    free_cash_flow: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    shares_outstanding: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    shares_outstanding_diluted: Mapped[BigInteger] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    current_ratio: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=2),
    )

    debt_to_assets_ratio: Mapped[Decimal] = mapped_column(
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
