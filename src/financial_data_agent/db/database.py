import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Return the configured database URL.

    Raises:
        RuntimeError: If `DATABASE_URL` is not set.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return database_url


@lru_cache(maxsize=1)
def get_engine():
    """Create and cache the SQLAlchemy engine."""
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Create and cache the SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for FastAPI dependencies."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
