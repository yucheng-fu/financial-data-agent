from types import SimpleNamespace

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


def test_fetch_filing_saves_through_the_injected_storage(monkeypatch) -> None:
    filing = SimpleNamespace(markdown=lambda: "# Filing", form="10-Q")

    class FakeCompany:
        def __init__(self, ticker: str) -> None:
            assert ticker == "AAPL"

        def get_filings(self, form: list[str], year: int, quarter: int, amendments: bool) -> list[object]:
            return [filing]

    monkeypatch.setattr(filings, "Company", FakeCompany)
    storage = FakeDataStorage()
    fetcher = filings.FilingsFetcher(storage=storage)

    location, returned_filing = fetcher.fetch_filing(ticker="aapl", form=["10-Q", "10-K"], quarter=2, year=2026)

    blob_name = "ticker=AAPL/year=2026/quarter=Q2/AAPL_2026_Q2/AAPL_2026_Q2.md"
    assert location == f"stored/{blob_name}"
    assert returned_filing is filing
    assert storage.saved == [(blob_name, "# Filing")]
