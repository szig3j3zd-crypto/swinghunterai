import concurrent.futures
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


# Yahoo Finance／J-Quantsへの要求頻度を抑えるための、ワーカー1つあたりの
# 取得間隔（2026-10-10改訂。以前は「IRBANK APIのレート制限に合わせた値」
# として1.1秒にしていたが、株価取得でIRBANKは使っていない（IRBANKは
# 銘柄一覧取得専用。ProviderManager参照）ため、その根拠自体が誤りだった。
# 「株価取得が遅い、速くできないか」との要望を受けて見直し、下記の
# 並列取得（MAX_WORKERS）と合わせて、安全マージンを残しつつ待機を短縮
# した。ワーカーごとにこの間隔を空けるため、合計のリクエスト頻度は
# おおよそMAX_WORKERS倍になる）
REQUEST_SLEEP = 0.5     # ワーカー1つあたりの待機（秒）
MAX_WORKERS = 5          # 同時に取得する銘柄数
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


def fetch_stock_data(ticker, latest_date):
    """
    1銘柄分の株価データをProvider経由で取得する
    （ネットワークI/Oのみ。DBへは一切アクセスしない）

    ThreadPoolExecutorのワーカーから呼ぶ想定（2026-10-10追加。「並列で
    取得することは可能なの？」との要望のため、取得（ネットワーク待ちが
    支配的）だけを並列化した。保存（DB書き込み）はmain()側でメイン
    スレッドから1件ずつ順番に行う。このプロジェクトのローカル実行は
    Turso Embedded Replicaモードを使っており、複数の接続が同時に同じ
    ローカルファイルへ書き込むと「database is locked」になる実績が
    本セッション中に複数回あったため、DBアクセス（get_latest_date・
    save_stock_data）は常にメインスレッドからのみ行うようにし、
    ワーカー側はネットワーク取得専用にしている。Provider（Yahoo/
    J-Quants）はいずれも呼び出しごとに新しいクライアントを作る作りで
    インスタンス変数を持たないため、並列呼び出しでも安全
    """

    try:
        return manager.download(
            ticker,
            latest_date
        )
    finally:
        time.sleep(REQUEST_SLEEP)


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

    # DBアクセス（最新保存日の取得）はメインスレッドでまとめて先に行う
    # （並列ワーカーにDBを触らせないため。2026-10-10追加）
    stock_rows = list(stocks.iterrows())
    latest_dates = {
        stock["code"]: get_latest_date(stock["code"])
        for _, stock in stock_rows
    }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_stock = {
            executor.submit(
                fetch_stock_data,
                stock["ticker"],
                latest_dates[stock["code"]]
            ): stock
            for _, stock in stock_rows
        }

        for index, future in enumerate(
            concurrent.futures.as_completed(future_to_stock),
            start=1
        ):

            stock = future_to_stock[future]

            code = stock["code"]
            ticker = stock["ticker"]
            company_name = stock["company_name"]
            latest_date = latest_dates[code]

            print("-" * 40)
            print(f"{code} 更新開始")

            if latest_date is None:
                print("初回取得")
            else:
                print(f"最新保存日 : {latest_date}")

            try:

                provider_name, stock_data = future.result()

                # Provider取得失敗（全Providerが例外で失敗した場合、
                # ProviderManagerはprovider_name=Noneを返す。2026-09-13
                # 修正: 以前はstock_data is Noneをチェックしていたが、
                # 全滅時もProviderManagerは空のDataFrame（Noneではない）を
                # 返すためこのチェックには到達せず、本当の取得失敗が下の
                # 「更新データなし」扱いになり、失敗としてカウント・
                # 記録されていなかった）
                if provider_name is None:

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
