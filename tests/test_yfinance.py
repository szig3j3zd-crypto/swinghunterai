import yfinance as yf

ticker = yf.Ticker("7203.T")

data = ticker.history(period="5d", auto_adjust=False)

print(type(data))
print(data)
print(len(data))