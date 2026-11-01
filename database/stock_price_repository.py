import pandas as pd

from database.db import create_connection

# 複数行INSERT 1文あたりの最大行数（1行7変数 × 500 = 3500変数。
# SQLiteのバインド変数上限より十分小さい値）
INSERT_CHUNK_ROWS = 500


def create_table():
    """
    stock_pricesテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            code TEXT,
            date TEXT,

            open REAL,
            high REAL,
            low REAL,
            close REAL,

            volume INTEGER,

            UNIQUE(code, date)
        )
        """
    )

    conn.commit()
    conn.close()


def save_stock_data(data, code, conn=None):
    """
    株価データを保存する。

    Parameters
    ----------
    data : pandas.DataFrame
        株価データ
    code : str
        銘柄コード
    conn : optional
        使い回すDB接続（2026-11-01追加）。渡した場合は閉じない。
        直接リモート接続を新規に作って最初のクエリを送るまでに1回あたり
        約85msかかるため、全銘柄を連続保存する株価更新スクリプトでは
        1本の接続を使い回す。省略時は従来通り毎回接続を作って閉じる

    Returns
    -------
    tuple
        insert_count : int
            新規保存件数

        duplicate_count : int
            重複件数
    """

    # 2026-10-17: Embedded Replica経由の書き込みは直接リモート接続より大幅に
    # 遅いことが実測で分かったため、書き込みはforce_remote=Trueで直接リモートへ
    # 行う（database.db.create_connectionのdocstring参照）
    own_conn = conn is None

    if own_conn:
        conn = create_connection(force_remote=True)

    cursor = conn.cursor()

    try:

        # 1行ずつexecute()していると、直接リモート接続では行数分の往復
        # （ネットワークラウンドトリップ）が発生し、データ量が多いと
        # 極端に遅くなる（2026-10-24発見・修正。yfinanceのperiod="max"化で
        # 1銘柄あたり最大6000行超を扱うようになった結果、1銘柄の保存だけで
        # 4分以上かかっていた。実測: 6687行の保存に272秒）。
        # 先に既存の日付一覧を1回のSELECTでまとめて取得し、新規行だけを
        # executemany()で1回にまとめて送ることで、往復回数を行数に関係なく
        # 2回（SELECT 1回・executemany 1回）に抑える
        #
        # 2026-11-01追記: 既存日付のSELECTは今回の取得データの期間内だけに
        # 絞る（通常の日次更新では数行〜十数行）。以前は銘柄の全期間
        # （最大6000行超）を毎回読んでおり、1銘柄あたり140〜500ms
        # かかっていた上、Tursoの行読み取り量も全銘柄で1回あたり
        # 約1000万行に達していた。絞り込み後は約30ms
        dates = pd.to_datetime(data["Date"]).dt.strftime("%Y-%m-%d")

        cursor.execute(
            "SELECT date FROM stock_prices "
            "WHERE code = ? AND date >= ? AND date <= ?",
            (code, dates.min(), dates.max())
        )
        existing_dates = {row[0] for row in cursor.fetchall()}

        rows_to_insert = []
        duplicate_count = 0

        for date, (_, row) in zip(dates, data.iterrows()):

            if date in existing_dates:
                duplicate_count += 1
                continue

            rows_to_insert.append((
                code,
                date,
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Volume"]
            ))

        # executemany()は直接リモート接続だと結局1行ごとに往復が発生し、
        # 10行でも約400〜650msかかっていた（2026-11-01実測）。
        # VALUES (...), (...), ... の複数行INSERT 1文にまとめると約80ms。
        # SQLiteのバインド変数上限を超えないよう、初回取得（数千行）時は
        # INSERT_CHUNK_ROWS行ずつに分ける
        for start in range(0, len(rows_to_insert), INSERT_CHUNK_ROWS):

            chunk = rows_to_insert[start:start + INSERT_CHUNK_ROWS]

            placeholders = ", ".join(
                ["(?, ?, ?, ?, ?, ?, ?)"] * len(chunk)
            )

            cursor.execute(
                "INSERT OR IGNORE INTO stock_prices "
                "(code, date, open, high, low, close, volume) "
                f"VALUES {placeholders}",
                [value for row in chunk for value in row]
            )

        insert_count = len(rows_to_insert)

        conn.commit()


    finally:

        if own_conn:
            conn.close()


    return (
        insert_count,
        duplicate_count
    )