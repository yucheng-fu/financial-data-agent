from __future__ import annotations

import pytest

from financial_data_agent.agent.tablerag.errors import DecompositionParseError
from financial_data_agent.agent.tablerag.parsing import AnswerAction, SubQueryAction, parse_decomposition


def test_parse_decomposition_reads_fenced_subquery_with_filters_and_sql() -> None:
    text = """Let me look up revenue first.
```json
{"action": "subquery", "subquery": "What was Apple's revenue in Q3 2024?",
 "tickers": ["AAPL"], "years": [2024], "quarters": [3], "sql": "SELECT 1"}
```"""

    assert parse_decomposition(text) == SubQueryAction(
        action="subquery",
        subquery="What was Apple's revenue in Q3 2024?",
        tickers=["AAPL"],
        years=[2024],
        quarters=[3],
        sql="SELECT 1",
    )


def test_parse_decomposition_reads_bare_answer() -> None:
    text = 'Done. {"action": "answer", "answer": "Revenue grew 5%."}'

    assert parse_decomposition(text) == AnswerAction(action="answer", answer="Revenue grew 5%.")


def test_parse_decomposition_defaults_missing_filters_and_sql() -> None:
    result = parse_decomposition('{"action": "subquery", "subquery": "Which companies are stored?"}')

    assert isinstance(result, SubQueryAction)
    assert (result.tickers, result.years, result.quarters, result.sql) == ([], [], [], None)


@pytest.mark.parametrize(
    "text",
    [
        "I cannot answer that.",
        '{"action": "answer"',
        '{"action": "search", "query": "revenue"}',
        '{"action": "answer"}',
    ],
)
def test_parse_decomposition_raises_on_unexpected_reply(text: str) -> None:
    with pytest.raises(DecompositionParseError):
        parse_decomposition(text)
