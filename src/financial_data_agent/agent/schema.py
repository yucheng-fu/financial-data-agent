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
  period_type = 'annual'. Never answer a quarter question with an annual row alone, or the reverse.
- If a quarter question has no 'quarterly' row in that slot but has an 'annual' row, the company filed its 10-K in
  that quarter (fiscal years differ by company). Then answer with both rows side by side from one query:
  the 'annual' row, labelled "full fiscal year ended <period_of_report>", and the company's latest 'quarterly' row
  with an earlier period_of_report, labelled "quarter ended <period_of_report>". Select ticker, reporting_year,
  reporting_quarter and period_type for both rows. Example for NVDA revenue, Q1 2020:
  WITH k AS (SELECT d.id, d.company_id, d.period_of_report FROM documents d JOIN companies c ON c.id = d.company_id
    WHERE c.ticker = 'NVDA' AND d.reporting_year = 2020 AND d.reporting_quarter = 1 AND d.period_type = 'annual')
  SELECT c.ticker, d.reporting_year, d.reporting_quarter, d.period_type, d.period_of_report, m.revenue
  FROM documents d JOIN companies c ON c.id = d.company_id JOIN financial_metrics m ON m.document_id = d.id
  WHERE d.id IN (SELECT id FROM k) OR d.id = (SELECT q.id FROM documents q JOIN k ON k.company_id = q.company_id
    WHERE q.period_type = 'quarterly' AND q.period_of_report < k.period_of_report
    ORDER BY q.period_of_report DESC LIMIT 1)
  For total_assets, total_liabilities, stockholders_equity, current_assets and ratios, state the change between
  the two rows. For income and cash-flow metrics never subtract one row from the other; show both with labels.
  In a 10-Q, revenue, operating_income and net_income cover the quarter, but operating_cash_flow,
  capital_expenditures and free_cash_flow are year to date, so label them "year to date".
- Only when the question asks for the change from the previous quarter or for a fiscal Q4 (never for a plain
  "what is the revenue" question, which keeps the two rows), do not use the two rows. Call
  get_fourth_quarter for the slot that holds the 10-K and answer from its result alone. With no ticker given,
  make the first query list the tickers with an 'annual' row and no 'quarterly' row in the slot, then call it for
  each. It returns single-quarter figures for the fiscal Q4 (fourth_quarter, year end fiscal_year_end) and the
  quarter before it (previous_quarter, ended previous_quarter_end); state the change (amount and percent) from
  previous_quarter to fourth_quarter. Example for Q1 2020:
  SELECT c.ticker FROM documents d JOIN companies c ON c.id = d.company_id
  WHERE d.reporting_year = 2020 AND d.reporting_quarter = 1 AND d.period_type = 'annual' AND NOT EXISTS (
    SELECT 1 FROM documents q WHERE q.company_id = d.company_id AND q.reporting_year = d.reporting_year
    AND q.reporting_quarter = d.reporting_quarter AND q.period_type = 'quarterly')
  For a 'quarterly' slot whose previous quarter is a fiscal Q4 (the latest earlier filing is a 10-K), call it for
  that 10-K's slot and compare its fourth_quarter with the 10-Q.
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
