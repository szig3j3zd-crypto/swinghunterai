from database.stock_reader import get_latest_date
from database.stock_repository import save_stock_data

from data.download_manager import DownloadManager
from data.failed_download_manager import FailedDownloadManager
from data.csv_writer import save_stock_csv


manager = DownloadManager()
failed_manager = FailedDownloadManager()


def main():

    failed_df = failed_manager.load()

    if failed_df.empty:

        print("再取得対象はありません。")

        return

    total = len(failed_df)

    success = 0
    error = 0

    retry_failed = []

    print("=" * 40)
    print("失敗銘柄再取得開始")
    print("=" * 40)

    print(f"対象 : {total}件")
    print()

    for _, row in failed_df.iterrows():

        code = row["code"]
        ticker = row["ticker"]
        company_name = row["company_name"]

        print("-" * 40)
        print(f"{code} 再取得")

        latest_date = get_latest_date(code)

        try:

            stock_data = manager.download(
                ticker,
                latest_date
            )

            if stock_data.empty:

                print("取得失敗")

                retry_failed.append(
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

            print(f"取得件数 : {len(stock_data)}件")
            print(f"新規保存 : {insert_count}件")
            print(f"重複     : {duplicate_count}件")

            success += 1

        except Exception as e:

            print(e)

            retry_failed.append(
                (
                    code,
                    ticker,
                    company_name
                )
            )

            error += 1

        manager.wait(1)

    if retry_failed:

        failed_manager.save(
            retry_failed
        )

        print()
        print(f"残り失敗銘柄 : {len(retry_failed)}件")

    else:

        failed_manager.clear()

        print()
        print("すべて取得完了")
        print("failed_download.csv を削除しました。")

    print()

    print("=" * 40)
    print("再取得完了")
    print("=" * 40)
    print(f"対象 : {total}")
    print(f"成功 : {success}")
    print(f"失敗 : {error}")
    print("=" * 40)


if __name__ == "__main__":
    main()