# from sec_edgar_downloader import Downloader

# dl = Downloader("data", "my.email@domain.com")

# dl.get("10-Q", "AAPL")

from pathlib import Path
from edgar import set_identity, Company

# Required by SEC fair access policy
set_identity("MyName my.email@domain.com")

# Target company and get filings for 2023 Q3
company = Company("AAPL")
filings = company.get_filings(form="10-Q", year=2023, quarter=3)

# Download/save the matching report as plain text
if filings:
    filing = filings[0]

    # Make sure the directory exists
    Path("data").mkdir(exist_ok=True)

    # Extract plain text content and save
    text_content = filing.text()
    file_path = Path("data") / "AAPL_2023_Q3.txt"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_content)

    print(f"Downloaded: {filing.form} filed on {filing.filing_date} to {file_path}")
