from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.constants import PERIOD_TYPES
from financial_data_agent.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from financial_data_agent.db.models.company import Company
    from financial_data_agent.db.models.document_chunk import DocumentChunk
    from financial_data_agent.db.models.financial_metric import FinancialMetric


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "period_type IN (" + ", ".join(f"'{period_type}'" for period_type in PERIOD_TYPES) + ")",
            name="ck_documents_period_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
    )

    accession_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reporting_year: Mapped[int] = mapped_column(
        nullable=False,
    )

    reporting_quarter: Mapped[int] = mapped_column(
        nullable=False,
    )

    period_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    filing_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    period_of_report: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    raw_document_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    company: Mapped[Company] = relationship(
        back_populates="documents",
    )

    financial_metrics: Mapped[list[FinancialMetric]] = relationship(
        back_populates="document",
    )

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
