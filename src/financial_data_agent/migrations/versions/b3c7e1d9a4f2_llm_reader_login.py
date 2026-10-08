"""llm reader login

Revision ID: b3c7e1d9a4f2
Revises: 9a2e6d4b1c8f
Create Date: 2026-10-03 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.engine import make_url

from financial_data_agent.config import require_env
from financial_data_agent.constants import LLM_READER_ROLE

# revision identifiers, used by Alembic.
revision: str = "b3c7e1d9a4f2"
down_revision: str | Sequence[str] | None = "9a2e6d4b1c8f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Let llm_reader log in with the password from `LLM_READER_DATABASE_URL`."""
    password = make_url(require_env("LLM_READER_DATABASE_URL")).password
    if not password:
        raise RuntimeError("LLM_READER_DATABASE_URL has no password")
    escaped = password.replace("'", "''")
    op.execute(f"ALTER ROLE {LLM_READER_ROLE} LOGIN PASSWORD '{escaped}'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"ALTER ROLE {LLM_READER_ROLE} NOLOGIN PASSWORD NULL")
