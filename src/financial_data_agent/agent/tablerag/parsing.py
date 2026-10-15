from __future__ import annotations

import json
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from financial_data_agent.agent.tablerag.errors import DecompositionParseError

FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
BARE_JSON_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)


class SubQueryAction(BaseModel):
    """The next subquery to solve, with the filings it concerns and optional SQL."""

    model_config = ConfigDict(frozen=True)

    action: Literal["subquery"]
    subquery: str
    tickers: list[str] = []
    years: list[int] = []
    quarters: list[int] = []
    sql: str | None = None


class AnswerAction(BaseModel):
    """The final answer to the original question."""

    model_config = ConfigDict(frozen=True)

    action: Literal["answer"]
    answer: str


DECOMPOSITION_ADAPTER: TypeAdapter[SubQueryAction | AnswerAction] = TypeAdapter(
    Annotated[SubQueryAction | AnswerAction, Field(discriminator="action")]
)


def parse_decomposition(text: str) -> SubQueryAction | AnswerAction:
    """Extract the decomposition decision from a model reply.

    Accepts the JSON object either inside a fenced code block or bare in the text.

    Args:
        text: The model's reply.

    Returns:
        The parsed subquery or final answer.

    Raises:
        DecompositionParseError: If no JSON object is found or it matches neither shape.
    """
    match = FENCED_JSON_PATTERN.search(text) or BARE_JSON_PATTERN.search(text)
    if match is None:
        raise DecompositionParseError(f"No JSON object in reply: {text!r}")
    try:
        return DECOMPOSITION_ADAPTER.validate_python(json.loads(match.group(1)))
    except (json.JSONDecodeError, ValidationError) as error:
        raise DecompositionParseError(str(error)) from error
