from __future__ import annotations

from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from financial_data_agent.agent.tablerag.state import TableRAGState, current_subquery
from financial_data_agent.constants import CHAT_SQL_ROW_LIMIT
from financial_data_agent.services.sql_query import execute_llm_sql


def run_sql(state: TableRAGState, reader_session: Session) -> dict[str, Any]:
    """Run the subquery's SQL as the read-only role.

    A database error is recorded rather than raised, so the intermediate answer can fall back to the text.

    Args:
        state: The subgraph state.
        reader_session: A session logged in as `llm_reader`.

    Returns:
        The query result, or the database error.

    Raises:
        RuntimeError: If the subquery carries no SQL.
    """
    sql = current_subquery(state).sql
    if sql is None:
        raise RuntimeError("route_sql sent a subquery without SQL to the sql node")
    try:
        return {"sql_result": execute_llm_sql(reader_session, sql, row_limit=CHAT_SQL_ROW_LIMIT)}
    except DBAPIError as error:
        message = str(error.orig)
        return {"sql_error": message, "errors": [message]}
