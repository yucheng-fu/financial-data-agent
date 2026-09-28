from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import polars as pl
import pytest

from financial_data_agent.constants import SP500_PARQUET_NAME
from financial_data_agent.ingestion import sp500
from financial_data_agent.ingestion.sp500 import SP500Fetcher

SP500_HTML = """
<table>
  <tr><th>Symbol</th><th>Security</th><th>CIK</th></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td><td>0000320193</td></tr>
  <tr><td>MSFT</td><td>Microsoft</td><td>0000789019</td></tr>
</table>
"""


class FakeDataStorage:
    """Record saved data instead of writing it anywhere."""

    def __init__(self) -> None:
        self.saved: list[tuple[str, bytes]] = []

    def save_text(self, blob_name: str, content: str) -> str:
        raise AssertionError("the S&P 500 table is saved as bytes")

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        self.saved.append((blob_name, content))
        return f"stored/{blob_name}"

    def read_text(self, blob_name: str) -> str:
        raise AssertionError("the S&P 500 table is not read back")


def test_fetch_keeps_leading_zeros_in_cik(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(text=SP500_HTML, raise_for_status=lambda: None)
    monkeypatch.setattr(sp500.requests, "get", lambda *args, **kwargs: response)

    frame = SP500Fetcher(storage=FakeDataStorage()).fetch(save_parquet=False)

    assert frame.schema["CIK"] == pl.String
    assert frame["CIK"].to_list() == ["0000320193", "0000789019"]


def test_fetch_saves_the_parquet_through_the_injected_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(text=SP500_HTML, raise_for_status=lambda: None)
    monkeypatch.setattr(sp500.requests, "get", lambda *args, **kwargs: response)
    storage = FakeDataStorage()

    frame = SP500Fetcher(storage=storage).fetch(save_parquet=True)

    assert [blob_name for blob_name, _ in storage.saved] == [SP500_PARQUET_NAME]
    saved_frame = pl.read_parquet(BytesIO(storage.saved[0][1]))
    assert saved_frame.equals(frame)


def test_fetch_does_not_save_when_save_parquet_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(text=SP500_HTML, raise_for_status=lambda: None)
    monkeypatch.setattr(sp500.requests, "get", lambda *args, **kwargs: response)
    storage = FakeDataStorage()

    SP500Fetcher(storage=storage).fetch(save_parquet=False)

    assert storage.saved == []
