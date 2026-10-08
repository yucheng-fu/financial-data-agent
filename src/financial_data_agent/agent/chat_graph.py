from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import partial
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from financial_data_agent.agent.schema import build_schema_prompt

SYSTEM_PROMPT = """\
You answer questions about S&P 500 companies and their SEC filings.
Use the query_database tool to look up facts; never invent numbers.
The database holds only the filings imported so far, so a result covering few companies or periods is expected.
Answer as soon as a query returns the data you need, and say which companies and periods it covers.
Do not re-run a query to double-check it. Write PostgreSQL against this schema:

{schema}"""


def call_model(
    state: MessagesState, model: Runnable[Sequence[BaseMessage], BaseMessage]
) -> dict[str, list[BaseMessage]]:
    """Ask the tool-bound chat model for the next message.

    The system prompt comes first so that providers can cache it across calls.

    Args:
        state: The conversation so far.
        model: The chat model with the tools bound.

    Returns:
        The model's reply, appended to the conversation by the graph.
    """
    system = SystemMessage(SYSTEM_PROMPT.format(schema=build_schema_prompt()))
    return {"messages": [model.invoke([system, *state["messages"]])]}


def build_chat_graph(chat_model: BaseChatModel, tools: Sequence[Callable[..., Any]]) -> CompiledStateGraph:
    """Compile the agent loop: the model calls tools until it can answer.

    Args:
        chat_model: The chat model that drives the conversation.
        tools: Functions the model may call.

    Returns:
        The compiled graph, to be invoked with a `recursion_limit`.
    """
    graph = StateGraph(MessagesState)
    graph.add_node("agent", partial(call_model, model=chat_model.bind_tools(tools)))  # Add node for agent
    graph.add_node("tools", ToolNode(tools))  # Add node for tool calling
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()
