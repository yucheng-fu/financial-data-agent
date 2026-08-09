from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_data_agent.db.models.base import Base

if TYPE_CHECKING:
    from financial_data_agent.db.models.document import Document


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(255))

    documents: Mapped[list[Document]] = relationship(back_populates="company")
