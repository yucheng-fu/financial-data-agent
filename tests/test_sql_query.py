from __future__ import annotations

import os
import socket

import pytest
from sqlalchemy import create_engine, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from financial_data_agent.db.database import get_readonly_session_factory
from financial_data_agent.db.DTO.company import CompanyDTO
from financial_data_agent.db.models.base import Base
from financial_data_agent.db.repositories.company import CompanyRepository
from financial_data_agent.services import sql_query
from financial_data_agent.services.sql_query import UnsafeSQLError, execute_readonly_sql, guard_select_sql


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def seed_companies(session: Session, count: int) -> None:
    repository = CompanyRepository(session)
    for index in range(count):
        repository.create(CompanyDTO(ticker=f"T{index}", name=f"Company {index}", cik=f"{index:010d}"))


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ticker FROM companies",
        "select ticker from companies;",
        'SELECT "CIK" FROM companies',
        "WITH t AS (SELECT ticker FROM companies) SELECT * FROM t",
        "(SELECT 1) UNION (SELECT 2)",
        "SELECT name FROM companies WHERE name = 'Update Inc'",
        "SELECT name FROM companies WHERE name = 'It''s; DROP TABLE x'",
        'SELECT 1 AS "delete"',
        "SELECT 1 -- DROP TABLE companies",
        "SELECT /* delete */ 1",
    ],
)
def test_guard_select_sql_accepts_reads_and_returns_them_unchanged(sql: str) -> None:
    assert guard_select_sql(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "  ;  ",
        "-- only a comment",
        "INSERT INTO companies (ticker) VALUES ('X')",
        "SELECT 1; DROP TABLE companies",
        "SELECT * FROM companies WHERE name = 'a'; DELETE FROM companies",
        "WITH t AS (DELETE FROM companies RETURNING *) SELECT * FROM t",
        "SELECT * INTO backup FROM companies",
        "SELECT set_config('transaction_read_only', 'off', true)",
        "/* SELECT */ UPDATE companies SET name = 'x'",
        "EXPLAIN ANALYZE DELETE FROM companies",
    ],
)
def test_guard_select_sql_rejects_writes_and_multiple_statements(sql: str) -> None:
    with pytest.raises(UnsafeSQLError):
        guard_select_sql(sql)


def test_execute_readonly_sql_returns_columns_and_rows() -> None:
    session = make_session()
    seed_companies(session, 2)

    result = execute_readonly_sql(session, "SELECT ticker, name FROM companies ORDER BY ticker")

    assert result.columns == ["ticker", "name"]
    assert result.rows == [("T0", "Company 0"), ("T1", "Company 1")]
    assert result.truncated is False


def test_execute_readonly_sql_truncates_at_the_row_limit() -> None:
    session = make_session()
    seed_companies(session, 3)

    result = execute_readonly_sql(session, "SELECT ticker FROM companies ORDER BY ticker", row_limit=2)

    assert result.rows == [("T0",), ("T1",)]
    assert result.truncated is True


def test_execute_readonly_sql_keeps_percent_and_colon_literals() -> None:
    session = make_session()
    seed_companies(session, 1)

    result = execute_readonly_sql(session, "SELECT ticker FROM companies WHERE name LIKE '%any 0' AND ':x' = ':x'")

    assert result.rows == [("T0",)]


def test_execute_readonly_sql_rejects_unsafe_sql_before_executing() -> None:
    session = make_session()
    seed_companies(session, 1)

    with pytest.raises(UnsafeSQLError):
        execute_readonly_sql(session, "DELETE FROM companies")

    assert len(CompanyRepository(session).list()) == 1


def test_execute_readonly_sql_rolls_back_the_transaction() -> None:
    session = make_session()

    execute_readonly_sql(session, "SELECT 1")

    assert not session.in_transaction()


def postgres_is_reachable() -> bool:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        return False
    url = make_url(database_url)
    try:
        socket.create_connection((url.host or "localhost", url.port or 5432), timeout=1).close()
    except OSError:
        return False
    return True


@pytest.mark.skipif(not postgres_is_reachable(), reason="needs a reachable PostgreSQL DATABASE_URL")
def test_readonly_transaction_rejects_a_write_that_bypasses_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sql_query, "guard_select_sql", lambda sql: sql)
    session = get_readonly_session_factory()()

    try:
        with pytest.raises(DBAPIError, match="read-only transaction"):
            execute_readonly_sql(session, "DELETE FROM companies WHERE false")
    finally:
        session.close()
