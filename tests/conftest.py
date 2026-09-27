from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from financial_data_agent.api.main import app
from financial_data_agent.db.database import get_session


@pytest.fixture(autouse=True)
def local_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the local environment so tests never reach for Azure Blob Storage.

    Tests covering deployed behavior set `ENVIRONMENT` themselves.
    """
    monkeypatch.setenv("ENVIRONMENT", "local")


@pytest.fixture(autouse=True)
def stub_db_session() -> Generator[None, None, None]:
    """Replace the `get_session` dependency so API tests never need a database.

    Tests that need a real session override `get_session` themselves.

    Yields:
        None while the override is active.
    """
    app.dependency_overrides[get_session] = lambda: MagicMock(spec=Session)
    yield
    app.dependency_overrides.clear()
