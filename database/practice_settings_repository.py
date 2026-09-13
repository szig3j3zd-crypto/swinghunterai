import sqlite3

from database.db import create_connection, sync_connection


def create_table():
    """
    practice_settingsテーブル作成

    練習チャートタブの設定を保持する、常に1行だけのテーブル（id=1固定）。
    売買記録（practice_trades）とは別テーブルにし、設定変更が記録の追加・
    編集と混ざらないようにする（2026-09-13追加）

    軍資金（initial_capital）に加え、直前に見ていた銘柄・チャートの
    表示状態（表示期間・表示幅・年月日検索）も保持し、練習チャートタブを
    開き直したときに同じ画面へ復元できるようにする
    （last_code/last_period_label/last_width_label/last_search_date、
    2026-09-13追加。「練習している銘柄を保存できるように。チャートで
    見ている日付や表示期間なども保存しておき、読み込んだら保存した日付に
    チャートが来るように」との要望のため）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_settings (

            id INTEGER PRIMARY KEY CHECK (id = 1),
            initial_capital REAL DEFAULT 0,

            last_code TEXT,
            last_period_label TEXT,
            last_width_label TEXT,
            last_search_date TEXT,

            updated_at TEXT

        )
        """
    )

    # 既存DB（last_*列がまだ無いテーブル）への追加マイグレーション。
    # 列が既にあればOperationalErrorになるので無視する
    for column_ddl in (
        "last_code TEXT",
        "last_period_label TEXT",
        "last_width_label TEXT",
        "last_search_date TEXT",
    ):
        try:
            cursor.execute(
                f"ALTER TABLE practice_settings ADD COLUMN {column_ddl}"
            )
        except (sqlite3.OperationalError, ValueError):
            # sqlite3はOperationalError、libsql（Turso接続時）はValueErrorを送出する
            pass

    conn.commit()
    conn.close()


def get_practice_settings():
    """
    練習チャートタブの設定を取得する

    Returns
    -------
    settings
        dict（initial_capital, last_code, last_period_label,
        last_width_label, last_search_date）。行が無い、または各列が
        未設定の場合はinitial_capital=0.0、それ以外はNone
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT initial_capital, last_code, last_period_label,
               last_width_label, last_search_date
        FROM practice_settings WHERE id = 1
        """
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return {
            "initial_capital": 0.0,
            "last_code": None,
            "last_period_label": None,
            "last_width_label": None,
            "last_search_date": None,
        }

    return {
        "initial_capital": row[0] if row[0] is not None else 0.0,
        "last_code": row[1],
        "last_period_label": row[2],
        "last_width_label": row[3],
        "last_search_date": row[4],
    }


def get_initial_capital():
    """
    練習チャートタブの初期軍資金（円）を取得する。未設定なら0
    """

    return get_practice_settings()["initial_capital"]


def update_initial_capital(initial_capital):
    """
    練習チャートタブの初期軍資金（円）を更新する（行が無ければ作成する）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM practice_settings WHERE id = 1")
    exists = cursor.fetchone() is not None

    if exists:
        cursor.execute(
            """
            UPDATE practice_settings
            SET initial_capital = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (initial_capital,)
        )
    else:
        cursor.execute(
            """
            INSERT INTO practice_settings (id, initial_capital, updated_at)
            VALUES (1, ?, datetime('now'))
            """,
            (initial_capital,)
        )

    conn.commit()
    sync_connection(conn)
    conn.close()


def update_last_practice_view(code, period_label, width_label, search_date):
    """
    直前に見ていた銘柄・チャートの表示状態（表示期間・表示幅・年月日検索）を
    更新する（行が無ければ作成する）。軍資金（initial_capital）は変更しない

    Parameters
    ----------
    code
        直前に検索していた銘柄コード（未選択ならNone）
    period_label
        表示期間のラベル（例:"5年"）
    width_label
        表示幅のラベル（例:"6ヶ月"）
    search_date
        年月日検索欄の値（"YYYY-MM-DD"文字列）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM practice_settings WHERE id = 1")
    exists = cursor.fetchone() is not None

    if exists:
        cursor.execute(
            """
            UPDATE practice_settings
            SET last_code = ?, last_period_label = ?, last_width_label = ?,
                last_search_date = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (code, period_label, width_label, search_date)
        )
    else:
        cursor.execute(
            """
            INSERT INTO practice_settings
            (id, last_code, last_period_label, last_width_label,
             last_search_date, updated_at)
            VALUES (1, ?, ?, ?, ?, datetime('now'))
            """,
            (code, period_label, width_label, search_date)
        )

    conn.commit()
    sync_connection(conn)
    conn.close()
