from __future__ import annotations

from typing import Literal

from langgraph.graph import END

from financial_data_agent.agent.tablerag.state import TableRAGState
from financial_data_agent.constants import METRIC_FIELDS

METRIC_NAMES: tuple[str, ...] = tuple(field.replace("_", " ") for field in METRIC_FIELDS)


def mentions_metric(text: str) -> bool:
    """Return whether the text names one of the stored financial metrics.

    Args:
        text: Text to check, typically a subquery.

    Returns:
        True if a metric name such as "free cash flow" appears in the text.
    """
    lowered = text.lower()
    return any(name in lowered for name in METRIC_NAMES)


def route_sql(state: TableRAGState) -> Literal["sql", "intermediate_answer"]:
    """Decide whether to run the subquery's SQL.

    Replaces the paper's "are there table chunks in the top-N?" test: SQL runs when a reranked
    chunk is a table or the subquery names a metric, and only if the model wrote SQL at all.

    Args:
        state: The subgraph state after reranking.

    Returns:
        The next node.
    """
    current = state["current"]
    if current is None or current.sql is None:
        return "intermediate_answer"
    if any(chunk.is_table for chunk in state["reranked"]) or mentions_metric(current.subquery):
        return "sql"
    return "intermediate_answer"


def route_after_decompose(state: TableRAGState) -> Literal["retrieve", "__end__"]:
    """End once there is an answer or the iteration budget is spent; otherwise solve the subquery.

    Args:
        state: The subgraph state after decomposition.

    Returns:
        The next node, or `END`.
    """
    if state["answer"] is not None or state["iteration"] > state["max_iterations"]:
        return END
    return "retrieve"
