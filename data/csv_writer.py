import os


def save_stock_csv(
    data,
    company_name,
    ticker
):
    """
    株価データをCSV保存
    """

    # 保存用データへ列名変更
    save_data = data.rename(
        columns={
            "Date": "日付",
            "Open": "始値",
            "High": "高値",
            "Low": "安値",
            "Close": "終値",
            "Volume": "出来高",
            "Dividends": "配当",
            "Stock Splits": "株式分割"
        }
    )

    # 保存フォルダ
    save_dir = "data/stock_data/daily"

    os.makedirs(
        save_dir,
        exist_ok=True
    )

    # ファイル名
    file_name = (
        f"{save_dir}/"
        f"{company_name}_{ticker.replace('.T', '')}.csv"
    )

    # CSV保存
    save_data.to_csv(
        file_name,
        index=False,
        encoding="utf-8-sig"
    )

    return file_name