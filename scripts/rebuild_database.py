from database.stock_price_repository import create_table as create_stock_price_table
from database.stock_master_repository import create_table as create_stock_master_table

print("データベースを作成します...")

create_stock_price_table()
create_stock_master_table()

print("データベース作成完了")