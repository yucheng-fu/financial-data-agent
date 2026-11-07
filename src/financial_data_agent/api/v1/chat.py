from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from financial_data_agent.api.requests.chat import ChatRequest
from financial_data_agent.api.responses.chat import (
    ChatResponse,
    ChatStepResponse,
    CitationResponse,
    TableRAGResponse,
    TokenUsageResponse,
)
from financial_data_agent.api.tools.acquire_filing import FilingAcquirer
from financial_data_agent.api.tools.list_available_filings import list_available_filings
from financial_data_agent.api.tools.query_database import query_database
from financial_data_agent.api.tools.table_rag import table_rag
from financial_data_agent.services.chat import ChatStep, ChatStepLimitError, answer_question

router = APIRouter(tags=["Chat"])

CITATION_COLUMNS = frozenset({"ticker", "reporting_year", "reporting_quarter", "period_type"})


@router.post("/chat", summary="Ask the agent a question")
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a question about the stored companies, filings and metrics.

    Args:
        request: The user's question.

    Returns:
        The answer, the filing chunks it cites, the tool calls (including any SQL) that produced it and the
        tokens spent.

    Raises:
        HTTPException: 422 if the agent does not reach an answer within the step limit; the
            detail carries the tool calls made and tokens spent before the limit was hit.
    """
    try:
        result = answer_question(
            request.message,
            tools=[query_database, table_rag, list_available_filings, FilingAcquirer().acquire_filing],
        )
    except ChatStepLimitError as error:
        detail = {
            "message": str(error),
            "steps": [to_step_response(step).model_dump() for step in error.steps],
            "usage": TokenUsageResponse.model_validate(error.usage, from_attributes=True).model_dump(),
        }
        raise HTTPException(status_code=422, detail=detail) from None
    steps = [to_step_response(step) for step in result.steps]
    return ChatResponse(
        answer=result.answer,
        citations=collect_citations(steps),
        steps=steps,
        usage=TokenUsageResponse.model_validate(result.usage, from_attributes=True),
    )


def to_step_response(step: ChatStep) -> ChatStepResponse:
    """Convert a service-level tool call into its response model.

    Args:
        step: The tool call made while answering.

    Returns:
        The tool call as an API response model.
    """
    result = {"error": step.result} if step.failed else json.loads(step.result)
    return ChatStepResponse(tool=step.tool, arguments=step.arguments, result=result)


def collect_citations(steps: list[ChatStepResponse]) -> list[CitationResponse]:
    """Gather the filings cited by table_rag chunks and by query_database rows that name their filing.

    Args:
        steps: The tool calls made while answering.

    Returns:
        The citations in the order they were returned.
    """
    citations = [
        citation
        for step in steps
        if step.tool == "table_rag"
        for citation in TableRAGResponse.model_validate(step.result).citations
    ]
    citations += [
        CitationResponse.model_validate({key: row.get(key) for key in CitationResponse.model_fields})
        for step in steps
        if step.tool == "query_database"
        for row in step.result.get("rows", [])
        if row.keys() >= CITATION_COLUMNS
    ]
    return list(dict.fromkeys(citations))
