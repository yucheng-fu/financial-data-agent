from financial_data_agent.agent.schema import build_schema_prompt
from financial_data_agent.constants import LLM_READER_TABLES, METRIC_FIELDS


def test_schema_prompt_quotes_cik_column() -> None:
    assert '"CIK" VARCHAR' in build_schema_prompt()


def test_schema_prompt_lists_every_granted_table_and_metric_field() -> None:
    prompt = build_schema_prompt()

    for table in LLM_READER_TABLES:
        assert f"CREATE TABLE {table} (" in prompt
    for field in METRIC_FIELDS:
        assert f"\t{field} NUMERIC" in prompt


def test_schema_prompt_places_periods_by_reporting_year_and_quarter() -> None:
    prompt = build_schema_prompt()

    assert "reporting_year = 2020 AND reporting_quarter = 1" in prompt
    assert "Never use period_of_report or filing_date to place a filing in a year or quarter" in prompt


def test_schema_prompt_ties_quarter_questions_to_quarterly_filings() -> None:
    prompt = build_schema_prompt()

    assert "A question about a quarter" in prompt
    assert "period_type = 'quarterly'" in prompt
    assert "Never answer a quarter question with an annual row" in prompt
