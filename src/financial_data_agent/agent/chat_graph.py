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
You answer questions about S&P 500 companies and their SEC filings; never invent numbers.
Tools:
- query_database: exact lookups of stored metrics, e.g. one company's revenue in one period.
  Always select c.ticker, d.reporting_year, d.reporting_quarter and d.period_type for each metric row;
  the API uses them to cite the filing, so do not repeat them in your answer unless asked.
- table_rag: questions that need filing text or several steps, e.g. comparisons or explanations.
  It is slow, so call it at most once per question and pass the whole question.
- list_available_filings: which filings are stored.
- acquire_filing: download a filing that is not stored. Use it only when a result says the filing is missing,
  at most once per period, and then repeat the earlier tool call.
The database holds only the filings imported so far, so a result covering few companies or periods is expected.
Answer as soon as a result gives you the data you need, and say which companies and periods it covers.
Do not re-run a call to double-check it. Write PostgreSQL against this schema:

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
