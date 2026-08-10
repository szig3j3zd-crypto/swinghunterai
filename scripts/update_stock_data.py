import sys
import time
from pathlib import Path

# python scripts/xxx.py で直接実行した場合、sys.path[0]はscripts/自身になり
# プロジェクトルートが見えないため、絶対importが解決できるよう明示的に追加する
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from database.stock_master_reader import get_active_stocks
from database.stock_price_reader import get_latest_date
from database.stock_price_repository import save_stock_data

from data.download_manager import DownloadManager
from data.csv_writer import save_stock_csv
from data.validator.data_validator import DataValidator

from logs.logger import save_download_history


# =====================================
# 設定
# =====================================


# IRBANK APIのレート制限（同一アカウント合算で60リクエスト/分、超過は429）に
# 収まるよう、1銘柄1リクエスト前提で60/60=1.0秒に安全マージンを乗せた値にする。
# 継続的にこの間隔を守れば429は原理的に発生しないため、旧仕様にあった
# 200銘柄ごとの追加待機（BATCH_SLEEP）は不要になり廃止した
REQUEST_SLEEP = 1.1      # 1銘柄待機
BATCH_SIZE = 200         # 200銘柄ごとに進捗表示のみ行う

manager = DownloadManager()


def save_failed_log(failed_list):
    """
    取得失敗銘柄保存
    """

    df = pd.DataFrame(
        failed_list,
        columns=[
            "code",
            "ticker",
            "company_name"
        ]
    )

    df.to_csv(
        "logs/failed_download.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("失敗ログ保存")
    print("logs/failed_download.csv")


def main():

    start_time = time.time()

    print("=" * 40)
    print("株価更新開始")
    print("=" * 40)

    stocks = get_active_stocks()

    # 動作確認中は3件だけ
    # stocks = stocks.head(3)

    total = len(stocks)

    success = 0
    error = 0

    yahoo_success = 0
    jquants_success = 0

    failed_list = []

    print(f"対象 : {total}件")
    print()

    for index, (_, stock) in enumerate(
        stocks.iterrows(),
        start=1
    ):

        code = stock["code"]
        ticker = stock["ticker"]
        company_name = stock["company_name"]

        print("-" * 40)
        print(f"{code} 更新開始")

        latest_date = get_latest_date(code)

        if latest_date is None:
            print("初回取得")
        else:
            print(f"最新保存日 : {latest_date}")

        try:

            provider_name, stock_data = manager.download(
                ticker,
                latest_date
            )

            # Provider取得失敗
            if stock_data is None:

                print("Provider取得失敗")

                failed_list.append(
                    (
                        code,
                        ticker,
                        company_name
                    )
                )

                error += 1

                continue

            # 更新不要
            if stock_data.empty:

                print("更新データなし")

                success += 1

                continue

            # データ品質チェック
            if not DataValidator.validate(
                stock_data
            ):

                print("データ検証失敗")

                failed_list.append(
                    (
                        code,
                        ticker,
                        company_name
                    )
                )

                error += 1

                continue

            insert_count, duplicate_count = save_stock_data(
                stock_data,
                code
            )

            save_stock_csv(
                stock_data,
                company_name,
                ticker
            )

            print(f"Provider : {provider_name}")
            print(f"取得件数 : {len(stock_data)}件")
            print(f"新規保存 : {insert_count}件")
            print(f"重複     : {duplicate_count}件")

            if provider_name == "Yahoo":
                yahoo_success += 1

            elif provider_name == "J-Quants":
                jquants_success += 1

            success += 1

        except Exception as e:

            print(e)

            failed_list.append(
                (
                    code,
                    ticker,
                    company_name
                )
            )

            error += 1

        time.sleep(REQUEST_SLEEP)

        if index % BATCH_SIZE == 0:

            print()

            print("=" * 40)
            print(f"{index}銘柄完了 / {total}")
            print("=" * 40)

    if failed_list:

        save_failed_log(
            failed_list
        )

    elapsed = time.time() - start_time

    save_download_history(
        total,
        success,
        error,
        yahoo_success,
        jquants_success,
        elapsed
    )

    print()
    print("=" * 40)
    print("株価更新完了")
    print("=" * 40)
    print(f"対象           : {total}")
    print(f"成功           : {success}")
    print(f"失敗           : {error}")
    print(f"Yahoo成功      : {yahoo_success}")
    print(f"J-Quants成功   : {jquants_success}")
    print(f"処理時間       : {elapsed:.1f}秒")
    print("=" * 40)


if __name__ == "__main__":
    main()