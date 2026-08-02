import pandas as pd
from database.db import create_connection

conn = create_connection()

query = """
SELECT
    code,
    date,
    COUNT(*) AS count
FROM stock_prices
GROUP BY code, date
HAVING COUNT(*) > 1
"""

df = pd.read_sql_query(query, conn)

conn.close()

if df.empty:
    print("[OK] 重複データはありません。")
else:
    print("[NG] 重複データがあります。")
    print(df)