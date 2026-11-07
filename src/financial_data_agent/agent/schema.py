from __future__ import annotations

from functools import lru_cache

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from financial_data_agent.constants import LLM_READER_TABLES
from financial_data_agent.db.models import Base

SCHEMA_NOTES = """\
Notes:
- Each row in documents is one SEC filing (10-Q or 10-K) of one company.
- documents.reporting_year and reporting_quarter are the calendar year and quarter in which the filing was filed.
  They define the period of a question: "Q1 2020" means reporting_year = 2020 AND reporting_quarter = 1.
  Never use period_of_report or filing_date to place a filing in a year or quarter.
- documents.period_type is 'quarterly' (10-Q, figures for one quarter) or 'annual' (10-K, figures for a whole year).
- A question about a quarter (for example "Q1 2020") needs period_type = 'quarterly'. A question about a year needs
  period_type = 'annual'. Never answer a quarter question with an annual row, or the reverse. If no row matches,
  say the figure is not in the database.
- financial_metrics.document_id references documents.id; join through documents to reach companies and periods.
- Never add or average annual and quarterly figures.
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
