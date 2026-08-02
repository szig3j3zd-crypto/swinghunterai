from database.stock_master_reader import get_active_stocks

stocks = get_active_stocks()

print(f"件数 : {len(stocks)}")
print(stocks["market"].value_counts())