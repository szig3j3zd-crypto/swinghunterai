import yfinance as yf


def get_stock_data(code):
    """
    株価データ取得
    """

    data = yf.download(
        code,
        period="1y",
        auto_adjust=False
    )


    # yfinanceのMultiIndex対応
    if hasattr(data.columns, "levels"):
        data.columns = data.columns.get_level_values(0)


    data = data.reset_index()


    return data



def get_company_name(code):
    """
    会社名取得
    """

    ticker = yf.Ticker(code)

    info = ticker.info

    return info.get(
        "longName",
        code
    )



def save_stock_csv(code):
    """
    株価データCSV保存
    """

    data = get_stock_data(code)


    company_name = get_company_name(code)


    data = data.rename(
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


    file_name = (
        f"data/stock_data/"
        f"{company_name}_{code.replace('.T','')}.csv"
    )


    data.to_csv(
        file_name,
        index=False,
        encoding="utf-8-sig"
    )


    return file_name