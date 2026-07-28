from io import StringIO
import pandas as pd
import polars as pl
import requests

URL = (
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks"
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}

# Fetch web content
response = requests.get(URL, headers=headers, timeout=30)
response.raise_for_status()

# Parse HTML tables
tables = pd.read_html(StringIO(response.text))

# Convert the primary table into a Polars DataFrame
df = pl.from_pandas(tables[0])

# Display the first few rows
print(df.head())
