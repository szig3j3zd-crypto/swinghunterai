import sys
import time
from datetime import date, timedelta
from pathlib import Path

# python scripts/xxx.py で直接実行した場合、sys.path[0]はscripts/自身になり
# プロジェクトルートが見えないため、絶対importが解決できるよう明示的に追加する
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import create_connection
from database.stock_price_repository import save_stock_data

from data.download_manager import DownloadManager
from data.csv_writer import save_stock_csv
from data.validator.data_validator import DataValidator

REQUEST_SLEEP = 1
DOWNLOAD_PERIOD = "10y"

manager = DownloadManager()


def get_short_history_prime_stocks():
    """
    プライム市場銘柄のうち、直近10年に満たない履歴しか
    持っていない銘柄を取得する。
    """

    cutoff = (date.today() - timedelta(days=365 * 10)).isoformat()

    conn = create_connection()

    query = """
    SELECT sm.code, sm.ticker, sm.company_name,
           MIN(sp.date) AS min_date
    FROM stock_master sm
    LEFT JOIN stock_prices sp ON sm.code = sp.code
    WHERE sm.active = 1
      AND sm.market = 'プライム（内国株式）'
    GROUP BY sm.code
    HAVING min_date IS NULL OR min_date > ?
    ORDER BY sm.code
    """

    import pandas as pd

    data = pd.read_sql_query(query, conn, params=(cutoff,))

    conn.close()

    return data


def main():

    start_time = time.time()

    print("=" * 40)
    print("プライム市場 10年データ拡張開始")
    print("=" * 40)

    stocks = get_short_history_prime_stocks()

    total = len(stocks)

    print(f"対象 : {total}件")

    success = 0
    error = 0

    for index, (_, stock) in enumerate(stocks.iterrows(), start=1):

        code = stock["code"]
        ticker = stock["ticker"]
        company_name = stock["company_name"]

        print("-" * 40)
        print(f"{code} {company_name} 拡張取得開始")

        try:

            provider_name, stock_data = manager.download(
                ticker=ticker,
                period=DOWNLOAD_PERIOD
            )

            if stock_data is None or stock_data.empty:
                print("取得失敗")
                error += 1
                continue

            if not DataValidator.validate(stock_data):
                print("データ検証失敗")
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

            success += 1

        except Exception as e:
            print(e)
            error += 1

        time.sleep(REQUEST_SLEEP)

    elapsed = time.time() - start_time

    print("=" * 40)
    print("プライム市場 10年データ拡張完了")
    print("=" * 40)
    print(f"対象 : {total}")
    print(f"成功 : {success}")
    print(f"失敗 : {error}")
    print(f"処理時間 : {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
