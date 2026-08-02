import sqlite3

conn = sqlite3.connect("data/stock.db")
cursor = conn.cursor()

cursor.execute("""
SELECT
    sm.code,
    sm.company_name
FROM stock_master sm
LEFT JOIN stock_prices sp
    ON sm.code = sp.code
WHERE sp.code IS NULL
ORDER BY sm.code
LIMIT 30
""")

rows = cursor.fetchall()

print("===== 未保存銘柄（先頭30件）=====")

for row in rows:
    print(row)

conn.close()
