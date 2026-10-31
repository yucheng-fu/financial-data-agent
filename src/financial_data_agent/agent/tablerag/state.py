from __future__ import annotations

from dataclasses import dataclass
from operator import add
from typing import Annotated, TypedDict, TypeVar

from financial_data_agent.agent.tablerag.constants import MAX_ITERATIONS
from financial_data_agent.agent.tablerag.parsing import SubQueryAction
from financial_data_agent.db.DTO.document_chunk import RetrievedChunk
from financial_data_agent.services.sql_query import SQLQueryResult

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SubAnswer:
    """A solved subquery and its intermediate answer."""

    subquery: str
    answer: str


@dataclass(frozen=True, slots=True)
class Citation:
    """A chunk an intermediate answer was based on."""

    ticker: str
    reporting_year: int
    reporting_quarter: int
    period_type: str
    accession_number: str
    chunk_index: int
    heading_path: str | None


@dataclass(frozen=True, slots=True)
class MissingFiling:
    """A filing a subquery needed but neither retrieval nor SQL could find."""

    ticker: str
    year: int
    quarter: int


def union(left: list[T], right: list[T]) -> list[T]:
    """Append the items of `right` not already in `left`, keeping order.

    Args:
        left: The accumulated items.
        right: The items returned by a node.

    Returns:
        The combined items without duplicates.
    """
    return [*left, *(item for item in dict.fromkeys(right) if item not in left)]


class TableRAGState(TypedDict):
    """State of the TableRAG subgraph; nodes return deltas, accumulators are merged by their reducers."""

    question: str
    iteration: int
    max_iterations: int
    current: SubQueryAction | None
    candidates: list[RetrievedChunk]
    reranked: list[RetrievedChunk]
    sql_result: SQLQueryResult | None
    sql_error: str | None
    answer: str | None
    history: Annotated[list[SubAnswer], add]
    errors: Annotated[list[str], add]
    citations: Annotated[list[Citation], union]
    missing: Annotated[list[MissingFiling], union]


def initial_state(question: str, max_iterations: int = MAX_ITERATIONS) -> TableRAGState:
    """Build the starting state for a question.

    Args:
        question: The question to answer.
        max_iterations: Maximum number of subqueries to solve before answering.

    Returns:
        The state with every key set.
    """
    return TableRAGState(
        question=question,
        iteration=0,
        max_iterations=max_iterations,
        current=None,
        candidates=[],
        reranked=[],
        sql_result=None,
        sql_error=None,
        answer=None,
        history=[],
        errors=[],
        citations=[],
        missing=[],
    )


def current_subquery(state: TableRAGState) -> SubQueryAction:
    """Return the subquery being solved.

    Args:
        state: The subgraph state.

    Returns:
        The current subquery.

    Raises:
        RuntimeError: If no subquery has been decomposed yet.
    """
    current = state["current"]
    if current is None:
        raise RuntimeError("No subquery to solve; decompose must run first")
    return current
