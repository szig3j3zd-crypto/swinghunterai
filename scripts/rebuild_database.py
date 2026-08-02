from database.db import (
    create_stock_table,
    create_stock_master_table
)

print("データベースを作成します...")

create_stock_table()
create_stock_master_table()

print("データベース作成完了")