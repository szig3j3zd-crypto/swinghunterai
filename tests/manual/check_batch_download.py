from data.download_manager import DownloadManager

manager = DownloadManager()

tickers = [
    "7203.T",
    "8306.T",
    "9432.T"
]

for ticker in tickers:

    provider_name, data = manager.download(ticker)

    print(ticker, provider_name, len(data), "件")

    print(data.head())

    print()
