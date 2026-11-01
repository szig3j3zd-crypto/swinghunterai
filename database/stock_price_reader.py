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


def get_latest_date(code, conn=None):
    """
    保存済み最新日付取得

    connを渡した場合はその接続を使い回し、閉じない（2026-11-01追加）。
    株価更新スクリプトが全銘柄（約3700件）分これを呼ぶ際、毎回
    create_connection()するとEmbedded Replicaの接続が銘柄数だけ作られ、
    それぞれのバックグラウンド同期（sync_interval）が同じレプリカファイルの
    WALを奪い合って「wal_insert_begin failed」「Failed to checkpoint WAL:
    database is locked」が大量に出ていた。呼び出し側で1本の接続を
    作って渡すことでこれを防ぐ
    """

    own_conn = conn is None

    if own_conn:
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

    if own_conn:
        conn.close()

    return latest_date