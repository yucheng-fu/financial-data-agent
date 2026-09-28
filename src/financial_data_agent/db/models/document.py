from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from financial_data_agent.db.models.company import Company
    from financial_data_agent.db.models.document_chunk import DocumentChunk
    from financial_data_agent.db.models.financial_metric import FinancialMetric


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

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

    year: Mapped[int] = mapped_column(
        nullable=False,
    )

    quarter: Mapped[int] = mapped_column(
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
