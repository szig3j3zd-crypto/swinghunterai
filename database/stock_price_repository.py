import pandas as pd

from database.db import create_connection


def create_table():
    """
    stock_pricesテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT,
            date TEXT,

            open REAL,
            high REAL,
            low REAL,
            close REAL,

            volume INTEGER,

            UNIQUE(code, date)
        )
        """
    )

    conn.commit()
    conn.close()


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

    # 2026-10-17: Embedded Replica経由の書き込みは直接リモート接続より大幅に
    # 遅いことが実測で分かったため、書き込みはforce_remote=Trueで直接リモートへ
    # 行う（database.db.create_connectionのdocstring参照）
    conn = create_connection(force_remote=True)

    cursor = conn.cursor()

    try:

        # 1行ずつexecute()していると、直接リモート接続では行数分の往復
        # （ネットワークラウンドトリップ）が発生し、データ量が多いと
        # 極端に遅くなる（2026-10-24発見・修正。yfinanceのperiod="max"化で
        # 1銘柄あたり最大6000行超を扱うようになった結果、1銘柄の保存だけで
        # 4分以上かかっていた。実測: 6687行の保存に272秒）。
        # 先に既存の日付一覧を1回のSELECTでまとめて取得し、新規行だけを
        # executemany()で1回にまとめて送ることで、往復回数を行数に関係なく
        # 2回（SELECT 1回・executemany 1回）に抑える
        cursor.execute(
            "SELECT date FROM stock_prices WHERE code = ?",
            (code,)
        )
        existing_dates = {row[0] for row in cursor.fetchall()}

        rows_to_insert = []
        duplicate_count = 0

        for _, row in data.iterrows():

            date = pd.to_datetime(
                row["Date"]
            ).strftime("%Y-%m-%d")

            if date in existing_dates:
                duplicate_count += 1
                continue

            rows_to_insert.append((
                code,
                date,
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Volume"]
            ))

        if rows_to_insert:

            cursor.executemany(
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
                rows_to_insert
            )

        insert_count = len(rows_to_insert)

        conn.commit()


    finally:

        conn.close()


    return (
        insert_count,
        duplicate_count
    )