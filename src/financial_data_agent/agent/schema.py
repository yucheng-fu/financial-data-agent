from __future__ import annotations

from functools import lru_cache

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from financial_data_agent.constants import LLM_READER_TABLES
from financial_data_agent.db.models import Base

SCHEMA_NOTES = """\
Notes:
- Each row in documents is one SEC filing (10-Q or 10-K) of one company.
- documents.reporting_year and reporting_quarter say WHEN the filing was filed (calendar year and quarter of
  filing_date). They do NOT say which period the figures are about. Never use them to answer a question about
  results in a year or quarter: a 10-K filed in Q1 reports the previous year.
- documents.period_type is 'quarterly' (10-Q, figures for one quarter) or 'annual' (10-K, figures for a whole year).
  documents.period_of_report is the end date of the period the figures cover.
- A question about a quarter (for example "Q1 2020") needs period_type = 'quarterly'. A question about a year needs
  period_type = 'annual'. Never answer a quarter question with an annual row, or the reverse. If no row matches,
  say the figure is not in the database.
- To find the filing for calendar quarter Q of year Y, filter on period_of_report, because companies' fiscal years
  differ: a quarterly filing belongs to the calendar quarter in which most of its three months fall, so
  period_of_report BETWEEN (first day of the quarter + 45 days) AND (last day of the quarter + 45 days).
  Q1 2020 is period_of_report BETWEEN '2020-02-15' AND '2020-05-15'. An annual filing belongs to the year in which
  most of its twelve months fall: period_of_report BETWEEN 'Y-07-01' AND '(Y+1)-06-30'.
- financial_metrics.document_id references documents.id; join through documents to reach companies and periods.
- Always say which period_of_report the figures cover, and never add or average annual and quarterly figures.
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
