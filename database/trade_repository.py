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

            trade_date TEXT,

            entry_price REAL,
            exit_price REAL,
            quantity INTEGER,

            created_at TEXT

        )
        """
    )

    conn.commit()
    conn.close()


def add_trade(code, company_name, direction, trade_date,
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
            trade_date,
            entry_price,
            exit_price,
            quantity,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            code,
            company_name,
            direction,
            trade_date,
            entry_price,
            exit_price,
            quantity
        )
    )

    conn.commit()
    conn.close()


def update_trade(trade_id, entry_price, exit_price, quantity):
    """
    売買銘柄の価格・株数を更新する（決済価格の後入力など）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE trades
        SET entry_price = ?, exit_price = ?, quantity = ?
        WHERE id = ?
        """,
        (
            entry_price,
            exit_price,
            quantity,
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


def get_all_trades():
    """
    売買銘柄を全件取得する

    Returns
    -------
    trades
        dictのリスト（id, code, company_name, direction, trade_date,
        entry_price, exit_price, quantity）。trade_date降順
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
        "trade_date",
        "entry_price",
        "exit_price",
        "quantity",
    ]

    rows = cursor.fetchall()

    conn.close()

    return [dict(zip(columns, row)) for row in rows]
