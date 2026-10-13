from __future__ import annotations

from functools import partial

from langchain_core.language_models import BaseChatModel
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from financial_data_agent.agent.tablerag.nodes.decompose import decompose
from financial_data_agent.agent.tablerag.nodes.intermediate_answer import intermediate_answer
from financial_data_agent.agent.tablerag.nodes.rerank import rerank_candidates
from financial_data_agent.agent.tablerag.nodes.retrieve import retrieve
from financial_data_agent.agent.tablerag.nodes.sql import run_sql
from financial_data_agent.agent.tablerag.routing import route_after_decompose, route_sql
from financial_data_agent.agent.tablerag.state import TableRAGState
from financial_data_agent.ingestion.embeddings import Embedder


def build_tablerag_graph(
    session: Session, reader_session: Session, chat_model: BaseChatModel, embedder: Embedder
) -> CompiledStateGraph:
    """Compile the TableRAG loop: decompose, retrieve, rerank, optionally run SQL, answer, repeat.

    Args:
        session: Database session used to search chunks.
        reader_session: A session logged in as `llm_reader`, used to run model-generated SQL.
        chat_model: The chat model for decomposition and intermediate answers.
        embedder: Embedding backend; must be the one the corpus was embedded with.

    Returns:
        The compiled graph, to be invoked with `recursion_limit_for(max_iterations)`.
    """
    graph = StateGraph(TableRAGState)
    graph.add_node("decompose", partial(decompose, model=chat_model))
    graph.add_node("retrieve", partial(retrieve, session=session, embedder=embedder))
    graph.add_node("rerank", rerank_candidates)
    graph.add_node("sql", partial(run_sql, reader_session=reader_session))
    graph.add_node("intermediate_answer", partial(intermediate_answer, model=chat_model))
    graph.add_edge(START, "decompose")
    graph.add_conditional_edges("decompose", route_after_decompose)
    graph.add_edge("retrieve", "rerank")
    graph.add_conditional_edges("rerank", route_sql)
    graph.add_edge("sql", "intermediate_answer")
    graph.add_edge("intermediate_answer", "decompose")
    return graph.compile()


def recursion_limit_for(max_iterations: int) -> int:
    """Return the graph step bound for an iteration budget.

    One decompose, then up to five nodes per iteration, plus one spare.

    Args:
        max_iterations: Maximum number of subqueries.

    Returns:
        The `recursion_limit` to invoke the graph with.
    """
    return 5 * max_iterations + 2
