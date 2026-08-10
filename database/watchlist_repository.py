import sqlite3

from database.db import create_connection


def create_table():
    """
    watchlistテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT,
            company_name TEXT,
            direction TEXT,
            timeframe TEXT DEFAULT 'daily',

            added_date TEXT,

            created_at TEXT

        )
        """
    )

    # 既存DB（timeframe列がまだ無いテーブル）への追加マイグレーション。
    # 列が既にあればOperationalErrorになるので無視する
    try:
        cursor.execute(
            "ALTER TABLE watchlist ADD COLUMN timeframe TEXT DEFAULT 'daily'"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def add_watchlist_stock(code, company_name, direction, timeframe, added_date):
    """
    監視銘柄を1件登録する
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO watchlist
        (
            code,
            company_name,
            direction,
            timeframe,
            added_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            code,
            company_name,
            direction,
            timeframe,
            added_date
        )
    )

    conn.commit()
    conn.close()


def update_watchlist_timeframe(watchlist_id, timeframe):
    """
    監視銘柄の時間足を更新する（日足/週足の登録間違いの修正用）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "UPDATE watchlist SET timeframe = ? WHERE id = ?",
        (timeframe, watchlist_id)
    )

    conn.commit()
    conn.close()


def delete_watchlist_stock(watchlist_id):
    """
    監視銘柄を1件削除する
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM watchlist WHERE id = ?",
        (watchlist_id,)
    )

    conn.commit()
    conn.close()


def get_all_watchlist_stocks():
    """
    監視銘柄を全件取得する

    Returns
    -------
    stocks
        dictのリスト（id, code, company_name, direction, timeframe,
        added_date）。added_date降順
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            code,
            company_name,
            direction,
            timeframe,
            added_date
        FROM watchlist
        ORDER BY added_date DESC, id DESC
        """
    )

    columns = ["id", "code", "company_name", "direction", "timeframe", "added_date"]

    rows = cursor.fetchall()

    conn.close()

    return [dict(zip(columns, row)) for row in rows]
