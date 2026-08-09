# プロジェクト名
PROJECT_NAME = "株探し"

# バージョン
VERSION = "2.1"

# 保存フォルダ
DATA_DIR = "data"

# ログフォルダ
LOG_DIR = "logs"

# 移動平均線期間
MA_PERIODS = {
    "short": 5,
    "mid": 20,
    "long": 60,
    "reference": 300,
}

# MA300（超長期線）をチャート表示するか
SHOW_MA300 = False

# 出来高平均の算出期間
VOLUME_AVG_WINDOW = 20

# 出来高フィルタ（この株数未満は候補から除外）
MIN_VOLUME = 500_000

# 株価フィルタ（Noneならフィルタなし）
MIN_PRICE = 1000
MAX_PRICE = 5000

# 時価総額フィルタ（Noneならフィルタなし。候補抽出後にYahoo Financeから取得して適用する）
MIN_MARKET_CAP = 500_000_000_000  # 5000億円
MAX_MARKET_CAP = None

# 支持線・抵抗線の検出期間（日数ベース）
SUPPORT_RESISTANCE_LOOKBACK = {
    "daily": 252,       # 直近1年（営業日ベース）
    "weekly": 156,      # 直近3年（週足本数ベース）
    "monthly": 84,      # 直近7年（月足本数ベース）
}

# スイングポイント検出: 前後何本より高値/安値なら候補とするか
SWING_POINT_WINDOW = 2

# 価格帯クラスタリング: 帯の平均値との差がこの割合以内なら同じ帯とする
ZONE_CLUSTER_THRESHOLD = 0.02

# ラインの採用条件
SR_MIN_TOUCH_COUNT = 3

# ラインの採用条件: 最初のタッチから最後のタッチまでの最低期間（日数）
SR_MIN_DURATION_DAYS = {
    "daily": 90,        # 3ヶ月
    "weekly": 180,      # 6ヶ月
    "monthly": 365,     # 1年
}

# ブレイク判定: ラインからこの割合を超えて終値が推移したらブレイク候補
SR_BREAKOUT_PCT = 0.01

# ブレイク判定: 何営業日連続でライン外側を維持したら正式ブレイク（ダマシ除外）とするか
SR_BREAKOUT_HOLD_DAYS = 3

# リセット条件: ラインからこの割合以上乖離したら対象外
SR_DEVIATION_RESET_PCT = 0.20

# リセット条件（ラインの有効期限）: 最終タッチからこの日数以上経過したら対象外
# 全時間足で共通の値を使う
SR_INACTIVITY_RESET_DAYS = 365

# 出来高による信頼度加点のしきい値（平均出来高の何倍以上か）
SR_VOLUME_CONFIDENCE_MULTIPLIER = 1.5

# エントリー候補の反発回数上限（これを超える反発は候補から除外）
MAX_ENTRY_BOUNCES = 2

# 近接した反発を1回にまとめる際の間隔（営業日ベース、行数の差で判定）
BOUNCE_MERGE_WITHIN_DAYS = 5

# 保有期間の警告しきい値（営業日）。利確・損切に未到達のままこの日数を超えたら
# 見直し候補として警告する（強制決済はしない）
MAX_HOLDING_DAYS = 20