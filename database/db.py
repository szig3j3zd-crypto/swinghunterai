import os
import sqlite3

from config.settings import TURSO_AUTH_TOKEN, TURSO_DATABASE_URL, TURSO_EMBEDDED_REPLICA

DB_PATH = "data/stock.db"

# PC側（Embedded Replicaモード）のローカルキャッシュファイル。既存のDB_PATH（プレーンな
# SQLiteファイル）とは別ファイルにし、libsqlのレプリカ管理と衝突しないようにする
EMBEDDED_REPLICA_PATH = "data/stock_replica.db"

# Embedded Replicaが書き込みをTursoへ自動同期する間隔（秒）
TURSO_SYNC_INTERVAL_SECONDS = 5


def create_connection():
    """
    DB接続。

    - pytest実行中は常にローカルSQLite（data/stock.db）へ接続する（テストがTursoへ
      書き込んでしまわないようにするための安全策。既存のテストの挙動を変えない）
    - Turso未設定（.envにTURSO_DATABASE_URL/TURSO_AUTH_TOKENが無い）の場合もローカル
      SQLiteへ接続する（後方互換）
    - TURSO_EMBEDDED_REPLICA=trueならローカルファイル+自動同期のEmbedded Replicaモード
      （PC用、読み書きが高速）
    - それ以外はTursoへ直接リモート接続する（Streamlit Community Cloud用、ローカル
      ディスクが永続化されない環境向け）
    """

    if os.getenv("PYTEST_CURRENT_TEST") or not (TURSO_DATABASE_URL and TURSO_AUTH_TOKEN):
        return sqlite3.connect(DB_PATH)

    import libsql

    if TURSO_EMBEDDED_REPLICA:
        return libsql.connect(
            EMBEDDED_REPLICA_PATH,
            sync_url=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
            sync_interval=TURSO_SYNC_INTERVAL_SECONDS,
        )

    return libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
