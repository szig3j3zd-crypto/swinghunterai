import time
import pandas as pd

from database.stock_master_reader import get_active_stocks
from database.stock_price_repository import create_table, save_stock_data

from data.download_manager import DownloadManager
from data.csv_writer import save_stock_csv
from data.validator.data_validator import DataValidator

from logs.logger import save_download_history

REQUEST_SLEEP = 0.3
BATCH_SIZE = 200
BATCH_SLEEP = 20
DOWNLOAD_PERIOD = "3y"

manager = DownloadManager()


def save_failed_log(failed_list):
    df = pd.DataFrame(
        failed_list,
        columns=["code", "ticker", "company_name"]
    )
    df.to_csv(
        "logs/failed_initialize.csv",
        index=False,
        encoding="utf-8-sig"
    )


def main():

    start_time = time.time()

    print("=" * 40)
    print("株価初期データ取得開始")
    print("=" * 40)

    create_table()

    stocks = get_active_stocks()

    # 初回は10銘柄程度で確認してください
    # stocks = stocks.head(10)

    total = len(stocks)

    success = 0
    error = 0
    yahoo_success = 0
    jquants_success = 0

    failed_list = []

    for index, (_, stock) in enumerate(stocks.iterrows(), start=1):

        code = stock["code"]
        ticker = stock["ticker"]
        company_name = stock["company_name"]

        print("-" * 40)
        print(f"{code} 初期取得開始")

        try:

            provider_name, stock_data = manager.download(
                ticker=ticker,
                period=DOWNLOAD_PERIOD
            )

            if stock_data is None or stock_data.empty:
                print("取得失敗")
                failed_list.append((code, ticker, company_name))
                error += 1
                continue

            if not DataValidator.validate(stock_data):
                print("データ検証失敗")
                failed_list.append((code, ticker, company_name))
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
            print(f"取得件数 : {len(stock_data)}")
            print(f"新規保存 : {insert_count}")
            print(f"重複 : {duplicate_count}")

            if provider_name == "Yahoo":
                yahoo_success += 1
            elif provider_name == "J-Quants":
                jquants_success += 1

            success += 1

        except Exception as e:
            print(e)
            failed_list.append((code, ticker, company_name))
            error += 1

        time.sleep(REQUEST_SLEEP)

        if index % BATCH_SIZE == 0:
            print("=" * 40)
            print(f"{index}/{total} 完了")
            print(f"{BATCH_SLEEP}秒待機")
            print("=" * 40)
            time.sleep(BATCH_SLEEP)

    if failed_list:
        save_failed_log(failed_list)

    elapsed = time.time() - start_time

    save_download_history(
        total,
        success,
        error,
        yahoo_success,
        jquants_success,
        elapsed
    )

    print("=" * 40)
    print("株価初期データ取得完了")
    print("=" * 40)
    print(f"対象 : {total}")
    print(f"成功 : {success}")
    print(f"失敗 : {error}")
    print(f"Yahoo成功 : {yahoo_success}")
    print(f"J-Quants成功 : {jquants_success}")
    print(f"処理時間 : {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
