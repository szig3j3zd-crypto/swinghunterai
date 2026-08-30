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
    except (sqlite3.OperationalError, ValueError):
        # sqlite3はOperationalError、libsql（Turso接続時）はValueErrorを送出する
        pass

    # 既存DB（priority列がまだ無いテーブル）への追加マイグレーション。
    # 優先監視銘柄かどうかのフラグ（0=通常、1=優先）。振り分けは監視銘柄
    # タブに追加した後に行うため、デフォルトは0（通常）
    try:
        cursor.execute(
            "ALTER TABLE watchlist ADD COLUMN priority INTEGER DEFAULT 0"
        )
    except (sqlite3.OperationalError, ValueError):
        pass

    conn.commit()
    conn.close()


def watchlist_stock_exists(code, direction, timeframe):
    """
    同じ銘柄コード・方向・時間足の監視銘柄が既に登録済みか確認する
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1 FROM watchlist
        WHERE code = ? AND direction = ? AND timeframe = ?
        LIMIT 1
        """,
        (code, direction, timeframe)
    )

    exists = cursor.fetchone() is not None

    conn.close()

    return exists


def add_watchlist_stock(code, company_name, direction, timeframe, added_date,
                         priority=False):
    """
    監視銘柄を1件登録する

    同じ銘柄コード・方向・時間足が既に登録済みの場合は二重登録せずスキップする。
    priority=Trueで優先監視銘柄として登録する（デフォルトは通常の監視銘柄）

    Returns
    -------
    added
        実際に登録した場合True、既に登録済みでスキップした場合False
    """

    if watchlist_stock_exists(code, direction, timeframe):
        return False

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
            priority,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            code,
            company_name,
            direction,
            timeframe,
            added_date,
            1 if priority else 0
        )
    )

    conn.commit()
    conn.close()

    return True


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


def update_watchlist_priority(watchlist_id, priority):
    """
    監視銘柄の優先フラグを更新する（優先監視銘柄⇔監視銘柄の振り分け用）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "UPDATE watchlist SET priority = ? WHERE id = ?",
        (1 if priority else 0, watchlist_id)
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


def delete_watchlist_stocks_by_code(code):
    """
    指定銘柄コードの監視銘柄をすべて削除する

    売買銘柄への追加時、「監視」から「保有」に卒業したものとして
    自動的に監視銘柄から取り除くために使う

    Returns
    -------
    deleted_count
        削除した件数
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM watchlist WHERE code = ?",
        (code,)
    )

    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted_count


def get_watchlist_codes():
    """
    監視銘柄として登録済みの銘柄コードの集合を取得する

    候補一覧から既に監視中の銘柄を除外するために使う

    Returns
    -------
    codes
        銘柄コードのset
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT code FROM watchlist")

    codes = {row[0] for row in cursor.fetchall()}

    conn.close()

    return codes


def get_all_watchlist_stocks():
    """
    監視銘柄を全件取得する

    Returns
    -------
    stocks
        dictのリスト（id, code, company_name, direction, timeframe,
        added_date, priority）。added_date昇順（古い順。新しく追加した銘柄が
        下に来るようにするため。2026-08-25改訂。以前は降順だった）。
        priorityは0/1の整数（1=優先監視銘柄）。優先/通常への振り分け自体は
        呼び出し側（ui/dashboard.py）で行う
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
            added_date,
            priority
        FROM watchlist
        ORDER BY added_date ASC, id ASC
        """
    )

    columns = [
        "id", "code", "company_name", "direction", "timeframe",
        "added_date", "priority",
    ]

    rows = cursor.fetchall()

    conn.close()

    return [dict(zip(columns, row)) for row in rows]
