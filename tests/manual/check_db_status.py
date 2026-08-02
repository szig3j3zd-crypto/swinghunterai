import sqlite3

conn = sqlite3.connect("data/stock.db")
cursor = conn.cursor()

print("===== stock_master =====")
cursor.execute("""
SELECT COUNT(*)
FROM stock_master
""")
print(cursor.fetchone()[0])

print()

print("===== stock_prices (保存済み銘柄数) =====")
cursor.execute("""
SELECT COUNT(DISTINCT code)
FROM stock_prices
""")
print(cursor.fetchone()[0])

print()

print("===== 保存件数TOP20 =====")
cursor.execute("""
SELECT
    code,
    COUNT(*)
FROM stock_prices
GROUP BY code
ORDER BY code
LIMIT 20
""")

for row in cursor.fetchall():
    print(row)

conn.close()
