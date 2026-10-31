from __future__ import annotations

from functools import lru_cache

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from financial_data_agent.constants import LLM_READER_TABLES
from financial_data_agent.db.models import Base

SCHEMA_NOTES = """\
Notes:
- Each row in documents is one SEC filing (10-Q or 10-K) of one company.
- documents.reporting_year and reporting_quarter say WHEN the filing was reported: the calendar year and quarter
  of filing_date. They are the same for every company, whatever its fiscal year. A 10-K filed in Q1 covers the
  previous fiscal year, so "Q1 2020" does not mean the quarter ending in March 2020.
- documents.period_type says WHAT the filing covers: 'quarterly' (10-Q) or 'annual' (10-K). An annual filing's income
  and cash flow figures cover a whole fiscal year, not a quarter. documents.period_of_report is the end date of the
  period covered; use it to compare companies by the period they report on.
- financial_metrics.document_id references documents.id; join through documents to reach companies and periods.
- Always filter on documents.period_type, and never add or average annual and quarterly figures.
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
    ddl = [str(CreateTable(Base.metadata.tables[name]).compile(dialect=dialect)).strip() for name in LLM_READER_TABLES]
    return "\n\n".join([*ddl, SCHEMA_NOTES])
