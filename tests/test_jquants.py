from jquantsapi import ClientV2

from config.settings import JQUANTS_API_KEY

client = ClientV2(
    api_key=JQUANTS_API_KEY
)

df = client.get_eq_bars_daily(
    code="1432"
)

print("===== Columns =====")
print(df.columns)

print()
print("===== Data =====")
print(df.head())

print()
print("===== OHLC =====")
print(
    df[
        [
            "Date",
            "O",
            "H",
            "L",
            "C",
            "Vo",
            "AdjO",
            "AdjH",
            "AdjL",
            "AdjC",
            "AdjVo"
        ]
    ].head()
)