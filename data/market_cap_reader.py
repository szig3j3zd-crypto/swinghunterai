import yfinance as yf


def get_market_cap(ticker):

    """
    Yahoo Financeから時価総額を取得する

    候補抽出後の絞り込み専用（対象件数が少ないため都度のライブ取得で足りる）。
    過去データとしてDBに保存はしない。

    Parameters
    ----------
    ticker
        "1301.T" 形式のティッカーコード

    Returns
    -------
    market_cap
        時価総額（円）。取得失敗時はNone
    """

    try:
        return yf.Ticker(ticker).fast_info.market_cap
    except Exception:
        return None
