from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from financial_data_agent.agent.schema import build_schema_prompt
from financial_data_agent.agent.tablerag.parsing import AnswerAction, parse_decomposition
from financial_data_agent.agent.tablerag.prompts import DECOMPOSE_PROMPT, LIMIT_NOTE
from financial_data_agent.agent.tablerag.state import SubAnswer, TableRAGState


def render_history(history: Sequence[SubAnswer]) -> str:
    """Render the solved subqueries for the decomposition prompt.

    Args:
        history: The subqueries solved so far, in order.

    Returns:
        One numbered subquery and answer per entry, or a placeholder when there are none.
    """
    if not history:
        return "None yet."
    return "\n".join(
        f"{number}. Subquery: {entry.subquery}\n   Answer: {entry.answer}" for number, entry in enumerate(history, 1)
    )


def decompose(state: TableRAGState, model: BaseChatModel) -> dict[str, Any]:
    """Ask the model for the next subquery, with its filters and SQL, or for the final answer.

    Clears the previous SQL result so that a subquery that skips SQL cannot reuse it.

    Args:
        state: The subgraph state.
        model: The chat model.

    Returns:
        The final answer, or the next subquery with the iteration counter advanced.

    Raises:
        DecompositionParseError: If the reply is not one of the two expected JSON shapes.
    """
    prompt = DECOMPOSE_PROMPT.format(
        schema=build_schema_prompt(),
        history=render_history(state["history"]),
        limit_note=LIMIT_NOTE if state["iteration"] >= state["max_iterations"] else "",
        question=state["question"],
    )
    action = parse_decomposition(model.invoke([HumanMessage(prompt)]).text)
    if isinstance(action, AnswerAction):
        return {"answer": action.answer}
    return {"current": action, "iteration": state["iteration"] + 1, "sql_result": None, "sql_error": None}
