from __future__ import annotations

import json
from collections.abc import Sequence
from itertools import product
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from financial_data_agent.agent.schema import build_schema_prompt
from financial_data_agent.agent.tablerag.parsing import SubQueryAction
from financial_data_agent.agent.tablerag.prompts import INTERMEDIATE_ANSWER_PROMPT
from financial_data_agent.agent.tablerag.state import (
    Citation,
    MissingFiling,
    SubAnswer,
    TableRAGState,
    current_subquery,
)
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk
from financial_data_agent.services.sql_query import SQLQueryResult


def render_docs(chunks: Sequence[RetrievedChunk]) -> str:
    """Render the reranked chunks for the intermediate-answer prompt.

    Args:
        chunks: The reranked chunks.

    Returns:
        Each chunk under a line naming its filing and section.
    """
    if not chunks:
        return "No passages found."
    return "\n\n".join(
        f"[{chunk.ticker} {chunk.year} Q{chunk.quarter} | {chunk.heading_path or 'no heading'}]\n{chunk.content}"
        for chunk in chunks
    )


def render_sql_result(result: SQLQueryResult | None, error: str | None) -> str:
    """Render the SQL outcome for the intermediate-answer prompt.

    Args:
        result: The query result, or None if the query did not run or failed.
        error: The database error, or None.

    Returns:
        The rows as JSON, the error, or a note that no SQL ran.
    """
    if error is not None:
        return f"SQL execution error: {error}"
    if result is None:
        return "SQL was not run."
    rows = [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    return json.dumps({"rows": rows, "truncated": result.truncated}, default=str)


def find_missing(
    current: SubQueryAction,
    candidates: Sequence[RetrievedChunk],
    result: SQLQueryResult | None,
) -> list[MissingFiling]:
    """Return the filings the subquery names that neither retrieval nor SQL found.

    Only filings named in full (ticker, year and quarter) are reported, since only those can be acquired.

    Args:
        current: The subquery.
        candidates: The chunks retrieved for it.
        result: The SQL result, or None if the SQL did not run or failed.

    Returns:
        The missing filings.
    """
    if result is not None and result.rows:
        return []

    found = {(chunk.ticker, chunk.year, chunk.quarter) for chunk in candidates}
    return [
        MissingFiling(ticker, year, quarter)
        for ticker, year, quarter in product(
            current.tickers, current.years, current.quarters
        )
        if (ticker, year, quarter) not in found
    ]


def intermediate_answer(state: TableRAGState, model: BaseChatModel) -> dict[str, Any]:
    """Answer the subquery by cross-validating the retrieved passages against the SQL result.

    Args:
        state: The subgraph state.
        model: The chat model.

    Returns:
        The subquery's answer, the chunks it cites, and any filings found missing.
    """
    current = current_subquery(state)
    sql_ran = state["sql_result"] is not None or state["sql_error"] is not None
    prompt = INTERMEDIATE_ANSWER_PROMPT.format(
        docs=render_docs(state["reranked"]),
        schema=build_schema_prompt(),
        sql=current.sql if sql_ran else "None",
        sql_result=render_sql_result(state["sql_result"], state["sql_error"]),
        query=current.subquery,
    )
    answer = model.invoke([HumanMessage(prompt)]).text
    citations = [
        Citation(
            chunk.ticker,
            chunk.year,
            chunk.quarter,
            chunk.accession_number,
            chunk.chunk_index,
            chunk.heading_path,
        )
        for chunk in state["reranked"]
    ]
    return {
        "history": [SubAnswer(current.subquery, answer)],
        "citations": citations,
        "missing": find_missing(current, state["candidates"], state["sql_result"]),
    }
