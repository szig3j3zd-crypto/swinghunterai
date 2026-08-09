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

    # 既存DB（nikkei225列がまだ無いテーブル）への追加マイグレーション。
    # 列が既にあればOperationalErrorになるので無視する
    try:
        cursor.execute(
            "ALTER TABLE stock_master ADD COLUMN nikkei225 INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
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
    size_class
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
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            nikkei225,
            size_class
        )
    )

    conn.commit()
    conn.close()


def add_stocks(stock_list):
    """
    複数銘柄登録
    """

    conn = create_connection()

    cursor = conn.cursor()

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
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        stock_list
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