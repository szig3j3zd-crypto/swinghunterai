import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from database.db import create_connection
import pandas as pd



def check_stock_data(code):
    """
    指定銘柄の株価データ確認
    """


    conn = create_connection()


    query = """
    SELECT *
    FROM stock_prices
    WHERE code = ?
    ORDER BY date DESC
    LIMIT 10
    """


    data = pd.read_sql_query(
        query,
        conn,
        params=(code,)
    )


    conn.close()


    return data



if __name__ == "__main__":


    result = check_stock_data(
        "7203"
    )


    print(result)