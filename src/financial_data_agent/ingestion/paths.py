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
