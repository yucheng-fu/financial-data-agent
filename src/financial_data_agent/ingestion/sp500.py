from io import BytesIO, StringIO

import pandas as pd
import polars as pl
import requests

from financial_data_agent.constants import SP500_PARQUET_NAME, SP500_WIKI_URL
from financial_data_agent.ingestion.storage import DataStorage, build_data_storage


class SP500Fetcher:
    """Fetch and optionally persist the current S&P 500 table from Wikipedia."""

    def __init__(self, storage: DataStorage | None = None) -> None:
        """Initialize the fetcher.

        Args:
            storage: Optional data storage backend.
        """
        self.url = SP500_WIKI_URL
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        }
        self.storage = storage or build_data_storage()

    def fetch(self, save_parquet: bool = True) -> pl.DataFrame:
        """Fetch the S&P 500 constituents table from Wikipedia.

        Args:
            save_parquet: Whether to persist the fetched table to the configured storage backend.

        Returns:
            The Wikipedia constituents table as a Polars DataFrame.
        """
        response = requests.get(self.url, headers=self.headers, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text), converters={"CIK": str})
        df = pl.from_pandas(tables[0])

        if save_parquet:
            buffer = BytesIO()
            df.write_parquet(buffer, compression="snappy")
            self.storage.save_bytes(SP500_PARQUET_NAME, buffer.getvalue())
        return df
