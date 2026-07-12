from database.stock_reader import get_stock_data_from_db
from indicators.moving_average import calculate_moving_average


# トヨタ株取得
df = get_stock_data_from_db(
    "7203"
)


print("取得データ")
print(df.head())


# 移動平均計算
result = calculate_moving_average(df)


print("計算後")
print(result.tail())