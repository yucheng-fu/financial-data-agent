from __future__ import annotations

import os
import socket

import pytest
from sqlalchemy import create_engine, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.db.database import get_llm_reader_session_factory
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.services.sql_query import execute_llm_sql


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def seed_companies(session: Session, count: int) -> None:
    repository = CompanyRepository(session)
    for index in range(count):
        repository.create(CompanyDTO(ticker=f"T{index}", name=f"Company {index}", cik=f"{index:010d}"))


def llm_reader_is_reachable() -> bool:
    database_url = os.getenv("LLM_READER_DATABASE_URL", "")
    if not database_url:
        return False
    url = make_url(database_url)
    try:
        socket.create_connection((url.host or "localhost", url.port or 5432), timeout=1).close()
    except OSError:
        return False
    return True


def test_execute_llm_sql_returns_columns_and_rows() -> None:
    session = make_session()
    seed_companies(session, 2)

    result = execute_llm_sql(session, "SELECT ticker, name FROM companies ORDER BY ticker")

    assert result.columns == ["ticker", "name"]
    assert result.rows == [("T0", "Company 0"), ("T1", "Company 1")]
    assert result.truncated is False


def test_execute_llm_sql_truncates_at_the_row_limit() -> None:
    session = make_session()
    seed_companies(session, 3)

    result = execute_llm_sql(session, "SELECT ticker FROM companies ORDER BY ticker", row_limit=2)

    assert result.rows == [("T0",), ("T1",)]
    assert result.truncated is True


def test_execute_llm_sql_keeps_percent_and_colon_literals() -> None:
    session = make_session()
    seed_companies(session, 1)

    result = execute_llm_sql(session, "SELECT ticker FROM companies WHERE name LIKE '%any 0' AND ':x' = ':x'")

    assert result.rows == [("T0",)]


def test_execute_llm_sql_rolls_back_the_transaction() -> None:
    session = make_session()

    execute_llm_sql(session, "SELECT 1")

    assert not session.in_transaction()


requires_llm_reader = pytest.mark.skipif(
    not llm_reader_is_reachable(), reason="needs a reachable LLM_READER_DATABASE_URL"
)


@requires_llm_reader
def test_llm_reader_can_select_from_granted_tables() -> None:
    session = get_llm_reader_session_factory()()

    try:
        result = execute_llm_sql(session, "SELECT count(*) FROM companies")
    finally:
        session.close()

    assert result.columns == ["count"]


@requires_llm_reader
@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM companies WHERE false",
        "WITH t AS (DELETE FROM companies WHERE false RETURNING *) SELECT * FROM t",
        "SELECT count(*) FROM document_chunks",
    ],
)
def test_llm_reader_is_denied_writes_and_ungranted_tables(sql: str) -> None:
    session = get_llm_reader_session_factory()()

    try:
        with pytest.raises(DBAPIError, match="permission denied"):
            execute_llm_sql(session, sql)
    finally:
        session.close()
