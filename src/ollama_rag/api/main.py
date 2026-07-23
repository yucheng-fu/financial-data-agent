from sec_edgar_downloader import Downloader

dl = Downloader("data", "my.email@domain.com")

dl.get("10-Q", "AAPL")
