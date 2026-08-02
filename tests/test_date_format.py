import pandas as pd
from database.db import create_connection

conn = create_connection()

query = """
SELECT
    code,
    date
FROM stock_prices
ORDER BY code, date
LIMIT 20
"""

df = pd.read_sql_query(query, conn)

conn.close()

print("===== 日付確認 =====")
print(df)