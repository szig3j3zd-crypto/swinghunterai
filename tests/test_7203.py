import sqlite3

conn = sqlite3.connect("data/stock.db")

count = conn.execute(
    """
    SELECT COUNT(*)
    FROM stock_prices
    WHERE code='7203'
    """
).fetchone()[0]

print("7203件数:", count)

conn.close()