import sqlite3

from database.db import create_connection, sync_connection


def create_table():
    """
    practice_tradesテーブル作成

    「練習チャート」タブ専用の売買記録。tradesテーブル（売買銘柄タブ、
    損益の税計算・NISA区分・決済日・時間足の記録を持つ）とは完全に別の
    テーブルにし、練習用の記録が実際の損益集計に混ざらないようにする
    （2026-09-13追加）。時間足は保存しない（チャート表示は他タブ同様、
    サイドバーの「時間足」に一本化するため、レコード自体が時間足を
    持つ必要が無い）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_trades (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT,
            company_name TEXT,
            direction TEXT,

            trade_date TEXT,
            exit_date TEXT,

            entry_price REAL,
            exit_price REAL,
            quantity INTEGER,

            created_at TEXT

        )
        """
    )

    # 既存DB（exit_date列がまだ無いテーブル）への追加マイグレーション。
    # 売却（決済）した日。「売った時の日付も入れれるように」との要望で
    # 2026-09-13に追加。列が既にあればOperationalErrorになるので無視する
    try:
        cursor.execute(
            "ALTER TABLE practice_trades ADD COLUMN exit_date TEXT"
        )
    except (sqlite3.OperationalError, ValueError):
        # sqlite3はOperationalError、libsql（Turso接続時）はValueErrorを送出する
        pass

    conn.commit()
    conn.close()


def add_practice_trade(code, company_name, direction, trade_date,
                        entry_price, exit_price, quantity, exit_date=None):
    """
    練習の売買記録を1件登録する

    exit_priceはNoneなら未決済（損益は計算対象外）として扱う。
    exit_dateは売却（決済）した日（未決済ならNoneのまま）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO practice_trades
        (
            code,
            company_name,
            direction,
            trade_date,
            exit_date,
            entry_price,
            exit_price,
            quantity,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            code,
            company_name,
            direction,
            trade_date,
            exit_date,
            entry_price,
            exit_price,
            quantity,
        )
    )

    conn.commit()
    sync_connection(conn)
    conn.close()


def update_practice_trade(practice_trade_id, direction, trade_date,
                           entry_price, exit_price, quantity, exit_date=None):
    """
    練習の売買記録の内容を更新する（表での直接編集用）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE practice_trades
        SET direction = ?, trade_date = ?, exit_date = ?, entry_price = ?,
            exit_price = ?, quantity = ?
        WHERE id = ?
        """,
        (
            direction,
            trade_date,
            exit_date,
            entry_price,
            exit_price,
            quantity,
            practice_trade_id,
        )
    )

    conn.commit()
    sync_connection(conn)
    conn.close()


def delete_practice_trade(practice_trade_id):
    """
    練習の売買記録を1件削除する
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM practice_trades WHERE id = ?",
        (practice_trade_id,)
    )

    conn.commit()
    sync_connection(conn)
    conn.close()


def get_all_practice_trades():
    """
    練習の売買記録を全件取得する

    Returns
    -------
    trades
        dictのリスト（id, code, company_name, direction, trade_date,
        exit_date, entry_price, exit_price, quantity）。trade_date昇順
        （古い順。新しく追加した記録ほど下に来る。trades/watchlistテーブルと
        同じ並び順の考え方）。exit_dateは売却（決済）した日の文字列または
        None（2026-09-13追加）
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
            trade_date,
            exit_date,
            entry_price,
            exit_price,
            quantity
        FROM practice_trades
        ORDER BY trade_date ASC, id ASC
        """
    )

    columns = [
        "id",
        "code",
        "company_name",
        "direction",
        "trade_date",
        "exit_date",
        "entry_price",
        "exit_price",
        "quantity",
    ]

    rows = cursor.fetchall()

    conn.close()

    return [dict(zip(columns, row)) for row in rows]
