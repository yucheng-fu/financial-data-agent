from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_data_agent.db.DTO.financial_metric import FinancialMetricDTO
from financial_data_agent.db.models.financial_metric import FinancialMetric


class FinancialMetricRepository:
    """Repository for CRUD operations on financial metric records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository.

        Args:
            session: Database session used for persistence.
        """
        self.session = session

    def create(self, financial_metric_dto: FinancialMetricDTO) -> FinancialMetric:
        """Create and persist financial metrics from a DTO.

        Args:
            financial_metric_dto: Financial metric values to persist.

        Returns:
            The persisted financial metrics.
        """
        financial_metric = FinancialMetric(**financial_metric_dto.to_model_kwargs())
        self.session.add(financial_metric)
        self.session.commit()
        self.session.refresh(financial_metric)
        return financial_metric

    def get_by_id(self, financial_metric_id: int) -> FinancialMetric | None:
        """Return financial metrics by primary key.

        Args:
            financial_metric_id: Primary key of the financial metrics.

        Returns:
            The financial metrics, or None if they do not exist.
        """
        return self.session.get(FinancialMetric, financial_metric_id)

    def get_by_document_id(self, document_id: int) -> FinancialMetric | None:
        """Return the financial metrics of a document.

        Args:
            document_id: Primary key of the document.

        Returns:
            The financial metrics, or None if the document has none.
        """
        statement = select(FinancialMetric).where(FinancialMetric.document_id == document_id)
        return self.session.scalar(statement)

    def list(self) -> Sequence[FinancialMetric]:
        """Return all financial metrics ordered by id.

        Returns:
            All financial metrics ordered by id.
        """
        statement = select(FinancialMetric).order_by(FinancialMetric.id)
        return self.session.scalars(statement).all()

    def update(self, financial_metric: FinancialMetric, financial_metric_dto: FinancialMetricDTO) -> FinancialMetric:
        """Update existing financial metrics from a DTO and persist the changes.

        Args:
            financial_metric: Financial metrics to update.
            financial_metric_dto: Values to apply; only supplied fields are written.

        Returns:
            The updated financial metrics.
        """
        financial_metric_dto.apply_to(financial_metric)
        self.session.commit()
        self.session.refresh(financial_metric)
        return financial_metric

    def delete(self, financial_metric: FinancialMetric) -> None:
        """Delete financial metrics from the database.

        Args:
            financial_metric: Financial metrics to delete.
        """
        self.session.delete(financial_metric)
        self.session.commit()
