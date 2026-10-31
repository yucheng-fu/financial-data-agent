"""document period type

Revision ID: 5e8a2f7c1b94
Revises: b3c7e1d9a4f2
Create Date: 2026-10-31 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e8a2f7c1b94"
down_revision: str | Sequence[str] | None = "b3c7e1d9a4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Name the document period as a reporting period, add its type, and drop the metric period columns."""
    op.alter_column("documents", "year", new_column_name="reporting_year")
    op.alter_column("documents", "quarter", new_column_name="reporting_quarter")
    op.add_column("documents", sa.Column("period_type", sa.String(length=10), nullable=True))
    op.execute("UPDATE documents SET period_type = CASE WHEN document_type = '10-K' THEN 'annual' ELSE 'quarterly' END")
    op.alter_column("documents", "period_type", nullable=False)
    op.create_check_constraint("ck_documents_period_type", "documents", "period_type IN ('quarterly', 'annual')")
    op.drop_column("financial_metrics", "period")
    op.drop_column("financial_metrics", "year")


def downgrade() -> None:
    """Restore the metric period columns from the reporting period of their document."""
    op.add_column("financial_metrics", sa.Column("period", sa.String(length=30), nullable=True))
    op.add_column("financial_metrics", sa.Column("year", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE financial_metrics SET period = 'Q' || documents.reporting_quarter, year = documents.reporting_year "
        "FROM documents WHERE documents.id = financial_metrics.document_id"
    )
    op.alter_column("financial_metrics", "period", nullable=False)
    op.alter_column("financial_metrics", "year", nullable=False)
    op.drop_constraint("ck_documents_period_type", "documents", type_="check")
    op.drop_column("documents", "period_type")
    op.alter_column("documents", "reporting_quarter", new_column_name="quarter")
    op.alter_column("documents", "reporting_year", new_column_name="year")
