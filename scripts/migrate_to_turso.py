"""ローカルのdata/stock.db（SQLite）をTurso（クラウドDB）へ一括移行する。

初回セットアップ専用。.envにTURSO_DATABASE_URL・TURSO_AUTH_TOKENが設定されている前提で、
Turso側にまだテーブルが無い状態（空のDB）へスキーマ・全データをコピーする。

再実行しても安全（INSERT OR IGNOREで既存行はスキップする）。
"""

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import libsql

from config.settings import TURSO_AUTH_TOKEN, TURSO_DATABASE_URL

SOURCE_DB_PATH = "data/stock.db"

# 1バッチあたりの行数。SQLiteのバインド変数上限（実測で20,000〜40,000の間）に
# 収まるよう、列数の多いテーブルでも安全な行数にしてある
BATCH_SIZE = 2000

TABLES = ["stock_master", "stock_prices", "trades", "watchlist"]


def get_schema_statements(source_conn):
    cur = source_conn.cursor()
    cur.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' "
        "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END"
    )
    return [row[2] for row in cur.fetchall() if row[2]]


def migrate_table(source_conn, dest_conn, table_name):
    src_cur = source_conn.cursor()
    src_cur.execute(f'SELECT * FROM "{table_name}"')
    columns = [d[0] for d in src_cur.description]
    column_list = ", ".join(f'"{c}"' for c in columns)
    row_placeholder = "(" + ", ".join("?" for _ in columns) + ")"

    dest_cur = dest_conn.cursor()
    total = 0
    start = time.time()

    while True:
        rows = src_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break

        # executemany()はリモートDBへ1行ずつ通信してしまい極端に遅いため
        # （1000件で約40秒）、1回のSQLに複数行のVALUESをまとめて送る
        # （同条件で約0.3秒、約100倍高速）
        values_sql = ", ".join(row_placeholder for _ in rows)
        insert_sql = (
            f'INSERT OR IGNORE INTO "{table_name}" ({column_list}) VALUES {values_sql}'
        )
        flat_params = [v for row in rows for v in row]

        dest_cur.execute(insert_sql, flat_params)
        dest_conn.commit()
        total += len(rows)
        elapsed = time.time() - start
        print(f"  {table_name}: {total}件 転送済み（{elapsed:.0f}秒経過）", flush=True)

    print(f"{table_name}: 完了、合計{total}件（{time.time() - start:.0f}秒）", flush=True)


def main():
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        raise SystemExit(
            ".envにTURSO_DATABASE_URL / TURSO_AUTH_TOKENを設定してから実行してください。"
        )

    source_conn = sqlite3.connect(SOURCE_DB_PATH)
    dest_conn = libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)

    print("スキーマを作成中...", flush=True)
    dest_cur = dest_conn.cursor()
    for statement in get_schema_statements(source_conn):
        try:
            dest_cur.execute(statement)
        except Exception as e:
            print(f"  スキップ（既存の可能性）: {e}")
    dest_conn.commit()
    print("スキーマ作成完了")

    for table_name in TABLES:
        migrate_table(source_conn, dest_conn, table_name)

    source_conn.close()
    dest_conn.close()
    print("移行完了")


if __name__ == "__main__":
    main()
