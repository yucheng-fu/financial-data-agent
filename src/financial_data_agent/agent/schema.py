from __future__ import annotations

from functools import lru_cache

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from financial_data_agent.constants import LLM_READER_TABLES
from financial_data_agent.db.models import Base

SCHEMA_NOTES = """\
Notes:
- Each row in documents is one SEC filing (10-Q or 10-K) of one company for one fiscal year and quarter.
- financial_metrics.document_id references documents.id; join through documents to reach companies.
- Filter quarters on documents.quarter, an integer from 1 to 4. Never filter on financial_metrics.period.
- "CIK" is a case-sensitive column and must always be written with double quotes.
- Monetary values are in USD, as reported in the filing."""


@lru_cache(maxsize=1)
def build_schema_prompt() -> str:
    """Render the PostgreSQL Data Definition Language (DDL) of the tables the model may query, followed by usage notes.

    The DDL is compiled from the SQLAlchemy models, so it cannot drift from them.

    Returns:
        The schema description for the system prompt.
    """
    dialect = postgresql.dialect()
    ddl = [
        str(CreateTable(Base.metadata.tables[name]).compile(dialect=dialect)).strip()
        for name in LLM_READER_TABLES
    ]
    return "\n\n".join([*ddl, SCHEMA_NOTES])
