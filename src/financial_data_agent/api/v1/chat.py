from __future__ import annotations

from fastapi import APIRouter, HTTPException

from financial_data_agent.api.requests.chat import ChatRequest
from financial_data_agent.api.responses.chat import ChatResponse, ChatStepResponse, QueryDatabaseResponse
from financial_data_agent.api.tools.query_database import query_database
from financial_data_agent.services.chat import ChatStep, ChatStepLimitError, answer_question

router = APIRouter(tags=["Chat"])


@router.post("/chat", summary="Ask the agent a question")
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a question about the stored companies, filings and metrics.

    Args:
        request: The user's question.

    Returns:
        The answer and the tool calls, including any SQL, that produced it.

    Raises:
        HTTPException: 422 if the agent does not reach an answer within the step limit; the
            detail carries the tool calls made before the limit was hit.
    """
    try:
        result = answer_question(request.message, tools=[query_database])
    except ChatStepLimitError as error:
        detail = {"message": str(error), "steps": [to_step_response(step).model_dump() for step in error.steps]}
        raise HTTPException(status_code=422, detail=detail) from None
    return ChatResponse(answer=result.answer, steps=[to_step_response(step) for step in result.steps])


def to_step_response(step: ChatStep) -> ChatStepResponse:
    """Convert a service-level tool call into its response model.

    Args:
        step: The tool call made while answering.

    Returns:
        The tool call as an API response model.
    """
    result = (
        QueryDatabaseResponse(error=step.result)
        if step.failed
        else QueryDatabaseResponse.model_validate_json(step.result)
    )
    return ChatStepResponse(tool=step.tool, arguments=step.arguments, result=result)
