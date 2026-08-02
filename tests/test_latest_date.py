from database.stock_reader import get_latest_date


print("===== 最新日付確認 =====")

latest = get_latest_date("7203")

print(latest)