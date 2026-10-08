from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from financial_data_agent.agent.chat_graph import build_chat_graph
from financial_data_agent.constants import CHAT_RECURSION_LIMIT
from financial_data_agent.ingestion.llm import get_chat_model


@dataclass(frozen=True, slots=True)
class ChatStep:
    """One tool call made while answering.

    `failed` is set when the call never reached the tool, e.g. an unknown tool name or invalid
    arguments; `result` is then the error text rather than the tool's output.
    """

    tool: str
    arguments: dict[str, Any]
    result: str
    failed: bool


class ChatStepLimitError(Exception):
    """Raised when the agent does not reach an answer within the step limit."""

    def __init__(self, message: str, steps: list[ChatStep]) -> None:
        """Initialize the error.

        Args:
            message: Description of the failure.
            steps: The tool calls made before the limit was hit.
        """
        super().__init__(message)
        self.steps = steps


@dataclass(frozen=True, slots=True)
class ChatResult:
    """The final answer and the tool calls that produced it."""

    answer: str
    steps: list[ChatStep]


def answer_question(
    message: str,
    tools: Sequence[Callable[..., Any]],
    chat_model: BaseChatModel | None = None,
) -> ChatResult:
    """Answer a single question, letting the chat model call the given tools.

    Args:
        message: The user's question.
        tools: Functions the model may call.
        chat_model: The chat model to use, or None for the configured one.

    Returns:
        The answer and every tool call made on the way.

    Raises:
        ChatStepLimitError: If the agent exceeds `CHAT_RECURSION_LIMIT` graph steps.
    """
    graph = build_chat_graph(chat_model or get_chat_model(), tools)
    messages: list[BaseMessage] = []

    # Run agent loop until it returns an answer or exceeds the CHAT_RECURSION_LIMIT.
    try:
        for state in graph.stream(
            {"messages": [HumanMessage(message)]},
            config={"recursion_limit": CHAT_RECURSION_LIMIT},
            stream_mode="values",
        ):
            messages = state["messages"]
    except GraphRecursionError:
        raise ChatStepLimitError(
            f"No answer within {CHAT_RECURSION_LIMIT} steps", collect_steps(messages)
        ) from None
    return ChatResult(answer=messages[-1].text, steps=collect_steps(messages))


def collect_steps(messages: Sequence[BaseMessage]) -> list[ChatStep]:
    """Pair each tool call with the tool's reply.

    Args:
        messages: The full conversation returned by the graph.

    Returns:
        The tool calls in the order they were made.
    """
    calls = {
        call["id"]: call
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    }
    return [
        ChatStep(
            tool=calls[message.tool_call_id]["name"],
            arguments=calls[message.tool_call_id]["args"],
            result=message.text,
            failed=message.status == "error",
        )
        for message in messages
        if isinstance(message, ToolMessage)
    ]
