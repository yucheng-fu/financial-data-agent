from io import StringIO
from pathlib import Path

import pandas as pd
import polars as pl
import requests

from financial_data_agent.constants import SP500_WIKI_URL


class SP500Fetcher:
    def __init__(self) -> None:
        self.url = SP500_WIKI_URL
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        }

    def fetch(self) -> pl.DataFrame:
        response = requests.get(self.url, headers=self.headers, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        df = pl.from_pandas(tables[0])

        Path("data").mkdir(exist_ok=True)
        df.write_parquet("data/s&p500.parquet", compression="snappy")
        return df


if __name__ == "__main__":
    fetcher = SP500Fetcher()
    df = fetcher.fetch()
    print(df)
