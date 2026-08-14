import sqlite3

from database.db import create_connection


def create_table():
    """
    tradesテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT,
            company_name TEXT,
            direction TEXT,
            timeframe TEXT DEFAULT 'daily',

            trade_date TEXT,

            entry_price REAL,
            exit_price REAL,
            quantity INTEGER,

            created_at TEXT

        )
        """
    )

    # 既存DB（timeframe列がまだ無いテーブル）への追加マイグレーション。
    # 列が既にあればOperationalErrorになるので無視する。DEFAULT 'daily'は
    # 既存行にも適用される（timeframeが無かった頃は日足での運用が前提だったため）
    try:
        cursor.execute(
            "ALTER TABLE trades ADD COLUMN timeframe TEXT DEFAULT 'daily'"
        )
    except (sqlite3.OperationalError, ValueError):
        # sqlite3はOperationalError、libsql（Turso接続時）はValueErrorを送出する
        pass

    conn.commit()
    conn.close()


def add_trade(code, company_name, direction, timeframe, trade_date,
              entry_price, exit_price, quantity):
    """
    売買銘柄を1件登録する

    exit_priceはNoneなら未決済（損益は集計対象外）として扱う
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO trades
        (
            code,
            company_name,
            direction,
            timeframe,
            trade_date,
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
            timeframe,
            trade_date,
            entry_price,
            exit_price,
            quantity
        )
    )

    conn.commit()
    conn.close()


def update_trade(trade_id, entry_price, exit_price, quantity, timeframe):
    """
    売買銘柄の価格・株数・時間足を更新する
    （決済価格の後入力、日足/週足の登録間違いの修正など）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE trades
        SET entry_price = ?, exit_price = ?, quantity = ?, timeframe = ?
        WHERE id = ?
        """,
        (
            entry_price,
            exit_price,
            quantity,
            timeframe,
            trade_id
        )
    )

    conn.commit()
    conn.close()


def delete_trade(trade_id):
    """
    売買銘柄を1件削除する
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM trades WHERE id = ?",
        (trade_id,)
    )

    conn.commit()
    conn.close()


def has_open_trade(code):
    """
    指定銘柄コードに未決済（保有中）のトレードがあるかどうか

    監視銘柄への追加時、既に保有中の銘柄を重複して監視登録しないための
    チェックに使う（決済済みのトレードは対象外）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM trades WHERE code = ? AND exit_price IS NULL LIMIT 1",
        (code,)
    )

    row = cursor.fetchone()

    conn.close()

    return row is not None


def get_all_trades():
    """
    売買銘柄を全件取得する

    Returns
    -------
    trades
        dictのリスト（id, code, company_name, direction, timeframe,
        trade_date, entry_price, exit_price, quantity）。trade_date降順
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
            trade_date,
            entry_price,
            exit_price,
            quantity
        FROM trades
        ORDER BY trade_date DESC, id DESC
        """
    )

    columns = [
        "id",
        "code",
        "company_name",
        "direction",
        "timeframe",
        "trade_date",
        "entry_price",
        "exit_price",
        "quantity",
    ]

    rows = cursor.fetchall()

    conn.close()

    return [dict(zip(columns, row)) for row in rows]
