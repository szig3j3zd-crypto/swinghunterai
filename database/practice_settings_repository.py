from database.db import create_connection, sync_connection


def create_table():
    """
    practice_settingsテーブル作成

    練習チャートタブの軍資金（元手）設定を保持する、常に1行だけの
    テーブル（id=1固定）。売買記録（practice_trades）とは別テーブルにし、
    軍資金の設定変更が記録の追加・編集と混ざらないようにする
    （2026-09-13追加）
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_settings (

            id INTEGER PRIMARY KEY CHECK (id = 1),
            initial_capital REAL DEFAULT 0,

            updated_at TEXT

        )
        """
    )

    conn.commit()
    conn.close()


def get_initial_capital():
    """
    練習チャートタブの初期軍資金（円）を取得する。未設定なら0
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT initial_capital FROM practice_settings WHERE id = 1")

    row = cursor.fetchone()

    conn.close()

    return row[0] if row else 0.0


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
