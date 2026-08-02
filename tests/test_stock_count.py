import sqlite3

conn = sqlite3.connect("data/stock.db")

cursor = conn.cursor()

cursor.execute("""
SELECT
    COUNT(DISTINCT code)
FROM stock_prices
""")

count = cursor.fetchone()[0]

print("===== 保存済み銘柄数 =====")
print(count)

conn.close()