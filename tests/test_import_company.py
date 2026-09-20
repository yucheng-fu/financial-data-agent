from __future__ import annotations

from financial_data_agent.ingestion.sp500 import _normalize_cik


def test_normalize_cik_pads_integer_values() -> None:
    assert _normalize_cik(320193) == "0000320193"


def test_normalize_cik_preserves_zero_padded_strings() -> None:
    assert _normalize_cik("0000320193") == "0000320193"


def test_normalize_cik_returns_none_for_empty_values() -> None:
    assert _normalize_cik(None) is None
    assert _normalize_cik("") is None
