from database.stock_master_reader import get_active_stocks
from database.stock_price_repository import save_stock_data
from data.download_manager import DownloadManager


manager = DownloadManager()


def download_all_stocks():
    """
    登録銘柄の株価データを一括取得・保存
    """


    stocks = get_active_stocks()


    total = len(stocks)

    success_count = 0
    error_count = 0


    print(
        f"取得対象銘柄数 : {total}"
    )


    for _, stock in stocks.iterrows():

        code = stock["code"]
        ticker = stock["ticker"]


        print(
            "\n--------------------"
        )

        print(
            f"{code} {ticker} 取得開始"
        )


        try:

            # 株価取得
            provider_name, data = manager.download(ticker)


            # データ取得失敗チェック
            if data.empty:

                print(
                    f"{code} データなし"
                )

                error_count += 1

                continue



            # DB保存
            save_stock_data(
                data,
                code
            )


            print(
                f"{code} 保存完了"
            )


            success_count += 1



        except Exception as e:

            print(
                f"{code} エラー発生"
            )

            print(
                e
            )

            error_count += 1



    print(
        "\n===================="
    )

    print(
        "株価取得処理完了"
    )

    print(
        f"成功 : {success_count}銘柄"
    )

    print(
        f"失敗 : {error_count}銘柄"
    )

    print(
        "===================="
    )