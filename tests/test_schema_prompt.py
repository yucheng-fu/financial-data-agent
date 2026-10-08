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


def test_schema_prompt_says_to_filter_on_documents_quarter() -> None:
    prompt = build_schema_prompt()

    assert "Filter quarters on documents.quarter" in prompt
    assert "Never filter on financial_metrics.period" in prompt
