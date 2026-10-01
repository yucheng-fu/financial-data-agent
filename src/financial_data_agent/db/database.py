import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Return the configured database URL.

    Returns:
        The database URL.

    Raises:
        RuntimeError: If `DATABASE_URL` is not set.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy engine.

    Returns:
        The shared SQLAlchemy engine.
    """
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Create and cache the SQLAlchemy session factory.

    Returns:
        The shared session factory.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_readonly_engine() -> Engine:
    """Return a view of the shared engine whose transactions are read-only on PostgreSQL.

    The view shares the parent engine's connection pool, and the option is ignored by other dialects.

    Returns:
        The read-only engine.
    """
    return get_engine().execution_options(postgresql_readonly=True)


@lru_cache(maxsize=1)
def get_readonly_session_factory() -> sessionmaker[Session]:
    """Create and cache the session factory bound to the read-only engine.

    Returns:
        The read-only session factory.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=get_readonly_engine())


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for FastAPI dependencies.

    Yields:
        A database session that is closed after use.
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
