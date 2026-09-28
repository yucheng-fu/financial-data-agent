from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financial_data_agent.constants import METRIC_FIELDS
from financial_data_agent.db.models.financial_metric import FinancialMetric


@dataclass(slots=True)
class FinancialMetricDTO:
    document_id: int | None = None
    revenue: Decimal | None = None
    operating_income: Decimal | None = None
    net_income: Decimal | None = None
    total_assets: Decimal | None = None
    total_liabilities: Decimal | None = None
    stockholders_equity: Decimal | None = None
    current_assets: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    capital_expenditures: Decimal | None = None
    free_cash_flow: Decimal | None = None
    shares_outstanding: Decimal | None = None
    shares_outstanding_diluted: Decimal | None = None
    current_ratio: Decimal | None = None
    debt_to_assets_ratio: Decimal | None = None
    period: str | None = None
    year: int | None = None
    supplied_fields: frozenset[str] = frozenset()

    def to_model_kwargs(self) -> dict[str, object | None]:
        """Convert the DTO to SQLAlchemy model keyword arguments.

        Returns:
            Keyword arguments for the financial metric model constructor.
        """
        return {
            "document_id": self.document_id,
            **{field: getattr(self, field) for field in METRIC_FIELDS},
            "period": self.period,
            "year": self.year,
        }

    def apply_to(self, financial_metric: FinancialMetric) -> FinancialMetric:
        """Apply DTO values to an existing financial metric model.

        Args:
            financial_metric: Financial metric model to update.

        Returns:
            The financial metric with the supplied fields applied.
        """
        for field in ("document_id", *METRIC_FIELDS, "period", "year"):
            if field in self.supplied_fields:
                setattr(financial_metric, field, getattr(self, field))
        return financial_metric
