from __future__ import annotations

from sqlalchemy.exc import DBAPIError

from financial_data_agent.api.responses.chat import QueryDatabaseResponse
from financial_data_agent.constants import CHAT_SQL_ROW_LIMIT
from financial_data_agent.db.database import get_llm_reader_session_factory
from financial_data_agent.services.sql_query import SQLQueryResult, execute_llm_sql


def query_database(sql: str) -> str:
    """Run one read-only PostgreSQL SELECT statement against the companies, documents and financial_metrics tables.

    Args:
        sql: A single PostgreSQL SELECT statement, written on one line.

    Returns:
        A `QueryDatabaseResponse` as JSON, holding the rows or the database error message.
    """
    try:
        with get_llm_reader_session_factory()() as session:
            result = execute_llm_sql(session, sql, row_limit=CHAT_SQL_ROW_LIMIT)
    except DBAPIError as error:
        return QueryDatabaseResponse(error=str(error.orig)).model_dump_json()
    return to_response(result).model_dump_json()


def to_response(result: SQLQueryResult) -> QueryDatabaseResponse:
    """Convert a query result into one object per row, keyed by column name.

    Args:
        result: The rows returned by the query.

    Returns:
        The rows and whether they were cut off at the row limit.
    """
    rows = [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    return QueryDatabaseResponse(rows=rows, truncated=result.truncated)
