import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from time import sleep

import polars as pl
from edgar import Company, set_identity

from financial_data_agent.constants import SEC_IDENTITY
from financial_data_agent.ingestion.storage import (
    DataStorage,
    build_data_storage,
    default_data_dir,
)


def parse_quarters(raw_quarters: list[str]) -> list[int]:
    """Parse quarter arguments that may be comma separated.

    Args:
        raw_quarters: Quarter values such as ['1', '2,3'].

    Returns:
        The quarters as integers.
    """
    quarters: list[int] = []
    for value in raw_quarters:
        quarters.extend(int(part) for part in value.split(",") if part)
    return quarters


def filing_blob_name(ticker: str, year: int, quarter: int) -> str:
    """Build the partitioned location of a filing markdown file.

    Args:
        ticker: Public company ticker symbol.
        year: Filing year.
        quarter: Calendar quarter, from 1 to 4.

    Returns:
        The relative filing location, using forward slashes.
    """
    symbol = ticker.upper()
    file_stem = f"{symbol}_{year}_Q{quarter}"
    return f"ticker={symbol}/year={year}/quarter=Q{quarter}/{file_stem}.md"


class FilingsFetcher:
    """Fetch and persist SEC filings."""

    def __init__(
        self,
        identity: str = SEC_IDENTITY,
        data_dir: Path | str | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        storage: DataStorage | None = None,
    ) -> None:
        """Initialize the fetcher.

        Args:
            identity: SEC fair access identity string.
            data_dir: Root directory used to store downloaded filings.
            max_retries: Maximum number of attempts for transient failures.
            retry_delay_seconds: Delay between retry attempts in seconds.
            storage: Optional data storage backend.
        """
        set_identity(identity)
        self.data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.storage = storage or build_data_storage(self.data_dir)

    def fetch_filing(
        self, ticker: str, form: list[str], quarter: int, year: int
    ) -> tuple[str, object]:
        """Fetch an SEC filing and save it to the configured storage backend.

        Args:
            ticker: Public company ticker symbol.
            form: SEC filing forms, such as ["10-Q", "10-K"].
            quarter: Calendar quarter, from 1 to 4.
            year: Filing year.

        Returns:
            A tuple containing the filing location, a disk path or blob name, and the filing.

        Raises:
            ValueError: If quarter is outside the range 1 to 4 or no filing is found.
        """
        if quarter not in {1, 2, 3, 4}:
            raise ValueError("quarter must be between 1 and 4")

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                company = Company(ticker.upper())
                filings = company.get_filings(
                    form=form, year=year, quarter=quarter, amendments=False
                )
                if not filings:
                    raise ValueError(
                        f"No {form} filing found for {ticker.upper()} in {year} Q{quarter}"
                    )

                filing = filings[0]
                location = self.storage.save_text(
                    filing_blob_name(ticker, year, quarter), filing.markdown()
                )
                return location, filing
            except TimeoutError as error:
                last_error = error
            except Exception as error:
                message = str(error).lower()
                if "timeout" not in message and "timed out" not in message:
                    raise
                last_error = error

            if attempt < self.max_retries:
                sleep(self.retry_delay_seconds * attempt)

        if last_error is not None:
            raise TimeoutError(
                f"Timed out fetching {form} for {ticker.upper()} after {self.max_retries} attempts"
            ) from last_error

        raise TimeoutError(f"Timed out fetching {form} for {ticker.upper()}")


class FilingsBackfillRunner:
    """Read S&P 500 tickers from parquet files and fetch recent SEC filings."""

    def __init__(
        self, data_dir: Path | str = "data", fetcher: FilingsFetcher | None = None
    ) -> None:
        """Initialize the runner.

        Args:
            data_dir: Directory containing parquet files and downloaded filings.
            fetcher: Optional filings fetcher instance.
        """
        self.data_dir = Path(data_dir)
        self.fetcher = fetcher or FilingsFetcher(data_dir=data_dir)

    def _current_period(self) -> tuple[int, int]:
        """Return the current calendar year and quarter.

        Returns:
            The current year and quarter.
        """
        today = date.today()
        quarter = (today.month - 1) // 3 + 1
        return today.year, quarter

    def _load_symbols(self) -> list[str]:
        """Load ticker symbols from parquet files in the data directory.

        Returns:
            Ticker symbols found in the parquet files.
        """
        symbols: list[str] = []
        for parquet_file in sorted(self.data_dir.glob("*.parquet")):
            frame = pl.read_parquet(parquet_file)
            if "Symbol" not in frame.columns:
                continue
            symbols.extend(
                frame.get_column("Symbol").drop_nulls().cast(pl.Utf8).to_list()
            )
        return symbols

    def run(
        self,
        limit: int = 5,
        year: int | None = None,
        quarter: int | None = None,
        max_workers: int = 5,
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Fetch filings for the first `limit` companies found in parquet files.

        Args:
            limit: Number of companies to process.
            year: Filing year. Defaults to the current year.
            quarter: Filing quarter. Defaults to the current quarter.
            max_workers: Maximum number of concurrent fetch operations.

        Returns:
            A tuple containing downloaded filing locations and failure records.
        """
        resolved_year, resolved_quarter = self._current_period()
        if year is not None:
            resolved_year = year
        if quarter is not None:
            resolved_quarter = quarter

        symbols = self._load_symbols()[:limit]
        downloaded_paths: list[str] = []
        failures: list[tuple[str, str]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(
                    self.fetcher.fetch_filing,
                    symbol,
                    ["10-Q", "10-K"],
                    resolved_quarter,
                    resolved_year,
                ): symbol
                for symbol in symbols
            }
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    file_path, _ = future.result()
                    downloaded_paths.append(file_path)
                except Exception as error:
                    failures.append((symbol, str(error)))
        return downloaded_paths, failures


def run_periods(
    runner: FilingsBackfillRunner,
    periods: list[tuple[int, int]],
    limit: int = 5,
    max_workers: int = 4,
) -> list[tuple[int, int, list[str], list[tuple[str, str]]]]:
    """Run the filings backfill for multiple year and quarter combinations.

    Args:
        runner: Filings backfill runner used to fetch filings.
        periods: Year and quarter pairs to process.
        limit: Number of companies to process per period.
        max_workers: Maximum number of concurrent period jobs.

    Returns:
        Period results including downloaded filing locations and failure records.
    """
    results: list[tuple[int, int, list[str], list[tuple[str, str]]]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_period = {
            executor.submit(runner.run, limit=limit, year=year, quarter=quarter): (
                year,
                quarter,
            )
            for year, quarter in periods
        }
        for future in as_completed(future_to_period):
            year, quarter = future_to_period[future]
            downloaded_paths, failures = future.result()
            results.append((year, quarter, downloaded_paths, failures))
    return results


def main() -> None:
    """Run the filings backfill workflow.

    Raises:
        SystemExit: If no parquet file with a Symbol column is found.
    """
    parser = argparse.ArgumentParser(
        description="Backfill SEC 10-Q filings from parquet tickers."
    )
    parser.add_argument(
        "--start-year", type=int, default=2022, help="Start year to process."
    )
    parser.add_argument(
        "--end-year", type=int, default=2025, help="End year to process."
    )
    parser.add_argument(
        "--quarters",
        nargs="+",
        default=["1", "2", "3", "4"],
        help="Quarter numbers to process.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of companies to process per period.",
    )
    parser.add_argument(
        "--max-period-workers",
        type=int,
        default=4,
        help="Maximum number of concurrent year-quarter jobs.",
    )
    parser.add_argument(
        "--max-symbol-workers",
        type=int,
        default=5,
        help="Maximum number of concurrent fetches per period.",
    )
    args = parser.parse_args()
    quarters = parse_quarters(args.quarters)

    runner = FilingsBackfillRunner()
    symbols = runner._load_symbols()
    if not symbols:
        print(f"No parquet files with a Symbol column were found in {runner.data_dir}")
        raise SystemExit(1)

    periods = [
        (year, quarter)
        for year in range(args.start_year, args.end_year + 1)
        for quarter in quarters
    ]
    results = run_periods(
        runner,
        periods,
        limit=args.limit,
        max_workers=args.max_period_workers,
    )

    for year, quarter, downloaded_paths, failures in sorted(
        results, key=lambda item: (item[0], item[1])
    ):
        for path in downloaded_paths:
            print(path)
        for symbol, error in failures:
            print(f"{year} Q{quarter} {symbol}: {error}")


if __name__ == "__main__":
    main()
