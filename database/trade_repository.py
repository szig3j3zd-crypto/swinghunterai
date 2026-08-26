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

    # 既存DB（is_nisa列がまだ無いテーブル）への追加マイグレーション。
    # NISA口座での取引かどうか（0=特定口座/課税、1=NISA/非課税）。
    # 損益計算（service.trade_service.calculate_pnl）で譲渡益課税を
    # 適用するかどうかの判定に使う
    try:
        cursor.execute(
            "ALTER TABLE trades ADD COLUMN is_nisa INTEGER DEFAULT 0"
        )
    except (sqlite3.OperationalError, ValueError):
        pass

    # 既存DB（exit_date列がまだ無いテーブル）への追加マイグレーション。
    # 決済日（決算株価を入力した実際の決済日）。未決済ならNULL
    try:
        cursor.execute(
            "ALTER TABLE trades ADD COLUMN exit_date TEXT"
        )
    except (sqlite3.OperationalError, ValueError):
        pass

    conn.commit()
    conn.close()


def add_trade(code, company_name, direction, timeframe, trade_date,
              entry_price, exit_price, quantity, is_nisa=False, exit_date=None):
    """
    売買銘柄を1件登録する

    exit_priceはNoneなら未決済（損益は集計対象外）として扱う。
    is_nisaはNISA口座での取引かどうか（Trueなら損益計算で非課税扱い）。
    exit_dateは決済日（決算株価が無ければNoneのまま）
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
            is_nisa,
            exit_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            code,
            company_name,
            direction,
            timeframe,
            trade_date,
            entry_price,
            exit_price,
            quantity,
            1 if is_nisa else 0,
            exit_date
        )
    )

    conn.commit()
    conn.close()


def update_trade(trade_id, entry_price, exit_price, quantity, timeframe,
                  trade_date, is_nisa=False, exit_date=None):
    """
    売買銘柄の価格・株数・時間足・取引日・NISA区分・決済日を更新する
    （決済価格の後入力、登録間違いの修正など）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE trades
        SET entry_price = ?, exit_price = ?, quantity = ?, timeframe = ?,
            trade_date = ?, is_nisa = ?, exit_date = ?
        WHERE id = ?
        """,
        (
            entry_price,
            exit_price,
            quantity,
            timeframe,
            trade_date,
            1 if is_nisa else 0,
            exit_date,
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
    チェックに使う（決算済みのトレードは対象外）
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


def get_open_trade_codes():
    """
    保有中（未決済）の売買銘柄コードの集合を取得する

    候補一覧から既に保有中の銘柄を除外するために使う
    （決算済みのトレードは対象外。再度候補として出てよいため）

    Returns
    -------
    codes
        銘柄コードのset
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT code FROM trades WHERE exit_price IS NULL")

    codes = {row[0] for row in cursor.fetchall()}

    conn.close()

    return codes


def get_all_trades():
    """
    売買銘柄を全件取得する

    Returns
    -------
    trades
        dictのリスト（id, code, company_name, direction, timeframe,
        trade_date, entry_price, exit_price, quantity, is_nisa, exit_date）。
        trade_date昇順（古い順。新しく追加した銘柄が下に来るようにするため。
        2026-08-25改訂。以前は降順だった）。is_nisaはbool
        （NISA口座での取引かどうか。2026-08-26追加。損益計算で非課税扱いに
        するかの判定に使う）。exit_dateは決済日の文字列またはNone
        （2026-08-26追加）
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
            quantity,
            is_nisa,
            exit_date
        FROM trades
        ORDER BY trade_date ASC, id ASC
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
        "is_nisa",
        "exit_date",
    ]

    def _to_dict(row):
        trade = dict(zip(columns, row))
        trade["is_nisa"] = bool(trade["is_nisa"])
        return trade

    rows = cursor.fetchall()

    conn.close()

    return [_to_dict(row) for row in rows]
