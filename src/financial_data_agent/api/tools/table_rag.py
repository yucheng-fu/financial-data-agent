from __future__ import annotations

from langgraph.errors import GraphRecursionError

from financial_data_agent.agent.tablerag.constants import MAX_ITERATIONS
from financial_data_agent.agent.tablerag.errors import DecompositionParseError
from financial_data_agent.agent.tablerag.graph import build_tablerag_graph, recursion_limit_for
from financial_data_agent.agent.tablerag.state import initial_state
from financial_data_agent.api.responses.chat import CitationResponse, MissingFilingResponse, TableRAGResponse
from financial_data_agent.db.database import get_llm_reader_session_factory, get_session_factory
from financial_data_agent.ingestion.embeddings import get_embedder
from financial_data_agent.ingestion.llm import get_chat_model


def table_rag(question: str) -> str:
    """Answer a question from the text and tables of the stored filings, breaking it into subquestions.

    Costs several model calls, so call it once per question. Use it for questions that need filing text or
    several steps, such as comparisons across companies or periods. When `missing` is not empty, the listed
    filings are not stored.

    Args:
        question: The complete question, naming the companies and periods it is about.

    Returns:
        A `TableRAGResponse` as JSON, holding the answer, the chunks it cites and any missing filings, or the
        error that stopped the call.
    """
    with get_session_factory()() as session, get_llm_reader_session_factory()() as reader_session:
        graph = build_tablerag_graph(session, reader_session, get_chat_model(), get_embedder())
        try:
            state = graph.invoke(
                initial_state(question), config={"recursion_limit": recursion_limit_for(MAX_ITERATIONS)}
            )
        except (GraphRecursionError, DecompositionParseError) as error:
            return TableRAGResponse(error=f"TableRAG failed: {error}").model_dump_json()
    return TableRAGResponse(
        answer=state["answer"],
        citations=[CitationResponse.model_validate(citation, from_attributes=True) for citation in state["citations"]],
        missing=[MissingFilingResponse.model_validate(item, from_attributes=True) for item in state["missing"]],
        error=None if state["answer"] else f"No answer within {MAX_ITERATIONS} subqueries",
    ).model_dump_json()
