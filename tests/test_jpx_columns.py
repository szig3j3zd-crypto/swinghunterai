import pandas as pd

df = pd.read_csv(
    "data/stock_data/master/prime.csv",
    encoding="cp932"
)

print(df.columns.tolist())