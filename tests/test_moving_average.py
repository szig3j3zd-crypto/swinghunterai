from database.stock_price_reader import get_stock_data
from indicators.moving_average import calculate_moving_average


# トヨタ株取得
df = get_stock_data(
    "7203"
)


print("取得データ")
print(df.head())


# 移動平均計算
result = calculate_moving_average(df)


print("計算後")
print(result.tail())