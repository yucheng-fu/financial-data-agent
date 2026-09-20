from __future__ import annotations

from types import SimpleNamespace

import polars as pl
import pytest

from financial_data_agent.ingestion import sp500
from financial_data_agent.ingestion.sp500 import SP500Fetcher

SP500_HTML = """
<table>
  <tr><th>Symbol</th><th>Security</th><th>CIK</th></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td><td>0000320193</td></tr>
  <tr><td>MSFT</td><td>Microsoft</td><td>0000789019</td></tr>
</table>
"""


def test_fetch_keeps_leading_zeros_in_cik(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(text=SP500_HTML, raise_for_status=lambda: None)
    monkeypatch.setattr(sp500.requests, "get", lambda *args, **kwargs: response)

    frame = SP500Fetcher().fetch(save_parquet=False)

    assert frame.schema["CIK"] == pl.String
    assert frame["CIK"].to_list() == ["0000320193", "0000789019"]
