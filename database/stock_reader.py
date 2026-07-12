import pandas as pd
from database.db import create_connection


def get_stock_data_from_db(code):
    """
    DBから株価取得
    """

    conn = create_connection()

    query = """
    SELECT *
    FROM stock_prices
    WHERE code = ?
    ORDER BY date
    """

    data = pd.read_sql_query(
        query,
        conn,
        params=(code,)
    )

    conn.close()

    return data