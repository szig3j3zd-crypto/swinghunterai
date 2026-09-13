from unittest.mock import MagicMock, patch

from database.db import sync_connection


def test_sync_connection_calls_sync_when_embedded_replica_enabled():
    conn = MagicMock()

    with patch("database.db.TURSO_EMBEDDED_REPLICA", True):
        sync_connection(conn)

    conn.sync.assert_called_once()


def test_sync_connection_skips_sync_when_not_embedded_replica():
    """
    2026-09-13追加: TURSO_EMBEDDED_REPLICA=false（Streamlit Community Cloud
    等、Tursoへ直接リモート接続する場合）ではsync()を呼ばない。直接リモート
    接続のlibsql.Connectionもsync属性自体は持つため、接続オブジェクトに
    sync属性があるかどうかだけでは判定できない。この修正前はCloud上で
    スマホから売買記録を追加するたびにsync()がエラーになりクラッシュ
    していた
    """

    conn = MagicMock()

    with patch("database.db.TURSO_EMBEDDED_REPLICA", False):
        sync_connection(conn)

    conn.sync.assert_not_called()


def test_sync_connection_handles_connection_without_sync_attribute():
    """
    sqlite3.Connection（テスト実行時・Turso未設定時）にはsync属性が無い。
    TURSO_EMBEDDED_REPLICA=trueであっても、そのようなオブジェクトを渡されて
    エラーにならないことを確認する
    """

    class _PlainConnection:
        pass

    conn = _PlainConnection()

    with patch("database.db.TURSO_EMBEDDED_REPLICA", True):
        sync_connection(conn)
