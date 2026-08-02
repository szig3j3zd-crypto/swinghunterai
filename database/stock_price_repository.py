import pandas as pd

from database.db import create_connection


def save_stock_data(data, code):
    """
    株価データを保存する。

    Parameters
    ----------
    data : pandas.DataFrame
        株価データ
    code : str
        銘柄コード

    Returns
    -------
    tuple
        insert_count : int
            新規保存件数

        duplicate_count : int
            重複件数
    """

    conn = create_connection()

    cursor = conn.cursor()

    insert_count = 0
    duplicate_count = 0

    try:

        for _, row in data.iterrows():

            date = pd.to_datetime(
                row["Date"]
            ).strftime("%Y-%m-%d")


            cursor.execute(
                """
                INSERT OR IGNORE INTO stock_prices
                (
                    code,
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code,
                    date,
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"]
                )
            )


            if cursor.rowcount == 1:
                insert_count += 1

            else:
                duplicate_count += 1


        conn.commit()


    finally:

        conn.close()


    return (
        insert_count,
        duplicate_count
    )