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


def test_schema_prompt_separates_the_filing_date_from_the_period_covered() -> None:
    prompt = build_schema_prompt()

    assert "WHEN the filing was filed" in prompt
    assert "Never use them to answer a question about" in prompt
    assert "period_of_report is the end date of the period the figures cover" in prompt


def test_schema_prompt_ties_quarter_questions_to_quarterly_filings() -> None:
    prompt = build_schema_prompt()

    assert "A question about a quarter" in prompt
    assert "period_type = 'quarterly'" in prompt
    assert "Never answer a quarter question with an annual row" in prompt
    assert "Q1 2020 is period_of_report BETWEEN '2020-02-15' AND '2020-05-15'" in prompt
