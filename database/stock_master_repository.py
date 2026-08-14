import sqlite3

from database.db import create_connection


def create_table():
    """
    stock_masterテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_master (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT UNIQUE,

            ticker TEXT UNIQUE,

            company_name TEXT,

            market TEXT,

            jpx400 INTEGER DEFAULT 0,

            nikkei225 INTEGER DEFAULT 0,

            size_class TEXT,

            active INTEGER DEFAULT 1

        )
        """
    )

    # 既存DB（新しい列がまだ無いテーブル）への追加マイグレーション。
    # 列が既にあればOperationalErrorになるので無視する
    try:
        cursor.execute(
            "ALTER TABLE stock_master ADD COLUMN nikkei225 INTEGER DEFAULT 0"
        )
    except (sqlite3.OperationalError, ValueError):
        # sqlite3はOperationalError、libsql（Turso接続時）はValueErrorを送出する
        pass

    try:
        cursor.execute(
            "ALTER TABLE stock_master ADD COLUMN market_cap REAL"
        )
    except (sqlite3.OperationalError, ValueError):
        pass

    conn.commit()
    conn.close()


def add_stock(
    code,
    ticker,
    company_name,
    market,
    jpx400,
    nikkei225,
    size_class,
    market_cap=None
):
    """
    1銘柄登録
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO stock_master
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class,
            market_cap,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class,
            market_cap
        )
    )

    conn.commit()
    conn.close()


def add_stocks(stock_list):
    """
    複数銘柄登録

    stock_listの各要素は
    (code, ticker, company_name, market, jpx400, nikkei225, size_class)
    または末尾にmarket_capを加えた8要素のタプル
    """

    conn = create_connection()

    cursor = conn.cursor()

    normalized = [
        row if len(row) == 8 else (*row, None)
        for row in stock_list
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO stock_master
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class,
            market_cap,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        normalized
    )

    conn.commit()
    conn.close()


def update_classification(stock_list):
    """
    market / jpx400 / nikkei225 / size_class のみ更新

    JPX公式CSV（市場区分・規模区分・JPX400・日経225）を反映する専用の更新。
    company_name / market_cap / active 等の他列には触れない
    （create_stock_master.py側で作成した内容を壊さないため）。

    Parameters
    ----------
    stock_list
        (code, ticker, company_name, market, jpx400, nikkei225, size_class)
        のタプルのリスト（ticker/company_nameは未使用）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.executemany(
        """
        UPDATE stock_master
        SET
            market = ?,
            jpx400 = ?,
            nikkei225 = ?,
            size_class = ?
        WHERE code = ?
        """,
        [
            (market, jpx400, nikkei225, size_class, code)
            for code, _ticker, _company_name, market, jpx400, nikkei225, size_class
            in stock_list
        ]
    )

    conn.commit()
    conn.close()


def get_all():
    """
    全銘柄取得
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class,
            market_cap,
            active
        FROM stock_master
        ORDER BY code
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_by_code(code):
    """
    コード検索
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class,
            market_cap,
            active
        FROM stock_master
        WHERE code=?
        """,
        (code,)
    )

    row = cursor.fetchone()

    conn.close()

    return row


def delete_all():
    """
    全削除
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM stock_master
        """
    )

    conn.commit()
    conn.close()