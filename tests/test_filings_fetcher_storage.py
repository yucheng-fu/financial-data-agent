from types import SimpleNamespace

import pytest

from financial_data_agent.ingestion import filings


class FakeDataStorage:
    """Record saved filings instead of writing them anywhere."""

    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []

    def save_text(self, blob_name: str, content: str) -> str:
        self.saved.append((blob_name, content))
        return f"stored/{blob_name}"

    def save_bytes(self, blob_name: str, content: bytes) -> str:
        raise AssertionError("filings are saved as text")

    def read_text(self, blob_name: str) -> str:
        raise AssertionError("the fetcher does not read filings back")


def patch_company(monkeypatch: pytest.MonkeyPatch, found: list[object]) -> None:
    class FakeCompany:
        def __init__(self, ticker: str) -> None:
            assert ticker == "NVDA"

        def get_filings(self, form: list[str], year: int, quarter: int, amendments: bool) -> list[object]:
            assert (year, quarter, amendments) == (2020, 1, False)
            return found

    monkeypatch.setattr(filings, "Company", FakeCompany)


def test_fetch_filings_saves_a_10k_and_a_10q_reported_in_the_same_quarter_separately(monkeypatch) -> None:
    annual = SimpleNamespace(markdown=lambda: "# 10-K", form="10-K")
    quarterly = SimpleNamespace(markdown=lambda: "# 10-Q", form="10-Q")
    patch_company(monkeypatch, [annual, quarterly])
    storage = FakeDataStorage()
    fetcher = filings.FilingsFetcher(storage=storage)

    fetched = fetcher.fetch_filings(ticker="nvda", form=["10-Q", "10-K"], quarter=1, year=2020)

    assert [(item.filing, item.period_type) for item in fetched] == [(annual, "annual"), (quarterly, "quarterly")]
    assert storage.saved == [
        ("ticker=NVDA/year=2020/quarter=Q1/NVDA_2020_Q1_annual.md", "# 10-K"),
        ("ticker=NVDA/year=2020/quarter=Q1/NVDA_2020_Q1_quarterly.md", "# 10-Q"),
    ]
    assert [item.location for item in fetched] == [f"stored/{name}" for name, _ in storage.saved]


def test_fetch_filings_raises_when_no_filing_was_reported(monkeypatch) -> None:
    patch_company(monkeypatch, [])
    fetcher = filings.FilingsFetcher(storage=FakeDataStorage())

    with pytest.raises(ValueError, match="No .* filing found"):
        fetcher.fetch_filings(ticker="NVDA", form=["10-Q", "10-K"], quarter=1, year=2020)


@pytest.mark.parametrize(("form", "expected"), [("10-K", "annual"), ("10-Q", "quarterly")])
def test_period_type_of_classifies_the_form(form: str, expected: str) -> None:
    assert filings.period_type_of(form) == expected
