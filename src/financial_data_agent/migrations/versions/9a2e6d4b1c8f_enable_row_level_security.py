"""enable row level security

Revision ID: 9a2e6d4b1c8f
Revises: 4f1a9c3e7b2d
Create Date: 2026-10-01 22:14:47.530912

"""

from collections.abc import Sequence

from alembic import op

from financial_data_agent.constants import LLM_READER_ROLE, LLM_READER_TABLES

# revision identifiers, used by Alembic.
revision: str = "9a2e6d4b1c8f"
down_revision: str | Sequence[str] | None = "4f1a9c3e7b2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_TABLES = ("alembic_version", "companies", "documents", "financial_metrics", "document_chunks")
LLM_READER_POLICY = "llm_reader_select"


def upgrade() -> None:
    """Upgrade schema."""
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    for table in LLM_READER_TABLES:
        op.execute(f"CREATE POLICY {LLM_READER_POLICY} ON {table} FOR SELECT TO {LLM_READER_ROLE} USING (true)")


def downgrade() -> None:
    """Downgrade schema."""
    for table in LLM_READER_TABLES:
        op.execute(f"DROP POLICY {LLM_READER_POLICY} ON {table}")
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
