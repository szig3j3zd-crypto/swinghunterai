import pandas as pd
from database.db import create_connection


def get_active_stocks():
    """
    分析対象銘柄を取得
    """

    conn = create_connection()

    query = """
    SELECT *
    FROM stock_master
    WHERE active = 1
      AND market IN (
            'プライム（内国株式）',
            'スタンダード（内国株式）',
            'グロース（内国株式）'
      )
    ORDER BY code
    """

    data = pd.read_sql_query(
        query,
        conn
    )

    conn.close()

    return data