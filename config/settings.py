import os

from dotenv import load_dotenv

load_dotenv()

JQUANTS_API_KEY = os.getenv(
    "JQUANTS_API_KEY",
    ""
)

IRBANK_API_KEY = os.getenv(
    "IRBANK_API_KEY",
    ""
)

IRBANK_BASE_URL = "https://api.irbank.net/v1"

# Turso（クラウドDB）。未設定ならdatabase/db.pyはローカルSQLiteのまま動作する
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

# PC側のみtrue（ローカルファイル+自動同期のEmbedded Replicaモードで高速に読み書きする）。
# Streamlit Community Cloud側は未設定のままにし、Tursoへ直接リモート接続する
TURSO_EMBEDDED_REPLICA = os.getenv("TURSO_EMBEDDED_REPLICA", "false").lower() == "true"

# ローカル開発中、Turso側の書き込み制限（プラン上限等）やネットワーク不調に
# 関わらずローカルSQLiteだけで動かしたいときにtrueにする（.envのみ、
# Streamlit Community Cloud側では未設定のままにする）
FORCE_LOCAL_SQLITE = os.getenv("FORCE_LOCAL_SQLITE", "false").lower() == "true"