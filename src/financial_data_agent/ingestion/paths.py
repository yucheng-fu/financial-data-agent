def filing_blob_name(ticker: str, reporting_year: int, reporting_quarter: int, period_type: str) -> str:
    """Build the partitioned location of a filing markdown file.

    Args:
        ticker: Public company ticker symbol.
        reporting_year: Calendar year the filing was reported in.
        reporting_quarter: Calendar quarter the filing was reported in, from 1 to 4.
        period_type: Whether the filing is "quarterly" or "annual".

    Returns:
        The relative filing location, using forward slashes.
    """
    symbol = ticker.upper()
    file_stem = f"{symbol}_{reporting_year}_Q{reporting_quarter}_{period_type}"
    return f"ticker={symbol}/year={reporting_year}/quarter=Q{reporting_quarter}/{file_stem}.md"
