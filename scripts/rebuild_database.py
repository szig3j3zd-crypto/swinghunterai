from database.stock_price_repository import create_table as create_stock_price_table
from database.stock_master_repository import create_table as create_stock_master_table
from database.trade_repository import create_table as create_trade_table
from database.watchlist_repository import create_table as create_watchlist_table

print("データベースを作成します...")

create_stock_price_table()
create_stock_master_table()
create_trade_table()
create_watchlist_table()

print("データベース作成完了")
