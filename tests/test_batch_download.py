from data.downloader import get_stock_data

tickers = [
    "7203.T",
    "8306.T",
    "9432.T"
]

data = get_stock_data(tickers)

print(type(data))

print()

print(data.head())

print()

print(data.columns)