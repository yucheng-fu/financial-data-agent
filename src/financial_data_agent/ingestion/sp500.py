from io import StringIO
from pathlib import Path

import pandas as pd
import polars as pl
import requests

from financial_data_agent.constants import SP500_WIKI_URL


def _normalize_cik(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        digits = cleaned.removeprefix("CIK").strip()
        if digits.isdigit():
            return digits.zfill(10)
        return cleaned
    if isinstance(value, int):
        return f"{value:010d}"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):010d}"
    return str(value)


class SP500Fetcher:
    """Fetch and optionally persist the current S&P 500 table from Wikipedia."""

    def __init__(self) -> None:
        self.url = SP500_WIKI_URL
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        }

    def fetch(self, save_parquet: bool = True) -> pl.DataFrame:
        """Fetch the S&P 500 constituents table from Wikipedia.

        Args:
            save_parquet: Whether to persist the fetched table to `data/s&p500.parquet`.

        Returns:
            The Wikipedia constituents table as a Polars DataFrame.
        """
        response = requests.get(self.url, headers=self.headers, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        table = tables[0].copy()
        if "CIK" in table.columns:
            table["CIK"] = table["CIK"].map(_normalize_cik)
        df = pl.from_pandas(table)

        Path("data").mkdir(exist_ok=True)
        if save_parquet:
            df.write_parquet("data/s&p500.parquet", compression="snappy")
        return df
