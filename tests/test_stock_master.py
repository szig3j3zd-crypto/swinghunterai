from database.stock_master_repository import get_all

stocks = get_all()

print(f"件数 : {len(stocks)}")

print()

for stock in stocks[:10]:
    print(stock)