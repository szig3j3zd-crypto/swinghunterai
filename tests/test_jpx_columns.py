import pandas as pd

df = pd.read_csv(
    "data/raw/jpx_list.csv",
    encoding="utf-8-sig"
)

print(df.columns.tolist())