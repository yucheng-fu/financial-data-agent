"""llm reader role

Revision ID: 4f1a9c3e7b2d
Revises: 7d4e2c81f9a3
Create Date: 2026-10-01 21:05:12.104377

"""

from collections.abc import Sequence

from alembic import op

from financial_data_agent.constants import LLM_READER_ROLE, LLM_READER_TABLES

# revision identifiers, used by Alembic.
revision: str = "4f1a9c3e7b2d"
down_revision: str | Sequence[str] | None = "7d4e2c81f9a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    tables = ", ".join(LLM_READER_TABLES)
    op.execute(f"CREATE ROLE {LLM_READER_ROLE} NOLOGIN")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {LLM_READER_ROLE}")
    op.execute(f"GRANT SELECT ON {tables} TO {LLM_READER_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    tables = ", ".join(LLM_READER_TABLES)
    op.execute(f"REVOKE SELECT ON {tables} FROM {LLM_READER_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {LLM_READER_ROLE}")
    op.execute(f"DROP ROLE {LLM_READER_ROLE}")
