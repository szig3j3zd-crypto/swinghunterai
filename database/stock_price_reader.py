import pandas as pd

from database.db import create_connection


def get_stock_data(code, limit=None):
    """
    指定銘柄の株価取得

    Parameters
    ----------
    code : str
        銘柄コード

    limit : int | None
        取得件数
        Noneなら全件取得
    """

    conn = create_connection()

    if limit is None:

        query = """
            SELECT *
            FROM stock_prices
            WHERE code = ?
            ORDER BY date
        """

        params = (code,)

    else:

        query = """
            SELECT *
            FROM stock_prices
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        """

        params = (
            code,
            limit
        )

    df = pd.read_sql_query(
        query,
        conn,
        params=params
    )

    conn.close()

    if limit is not None:
        df = df.sort_values("date")

    return df


def get_latest_date(code):
    """
    保存済み最新日付取得
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT MAX(date)
        FROM stock_prices
        WHERE code = ?
        """,
        (code,)
    )

    latest_date = cursor.fetchone()[0]

    conn.close()

    return latest_date