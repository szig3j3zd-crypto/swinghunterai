import time

import pandas as pd
import yfinance as yf

from data.providers.base_provider import BaseProvider


class YahooProvider(BaseProvider):
    """
    Yahoo Finance Provider
    """

    @property
    def name(self):
        return "Yahoo"

    def is_available(self):
        """
        Yahoo Financeは常に利用可能
        """
        return True

    def get_stock_data(
        self,
        ticker,
        latest_date=None,
        period="1y",
        retry=3
    ):
        """
        Yahoo Financeから株価取得
        """

        ticker_obj = yf.Ticker(ticker)

        for attempt in range(retry):

            try:

                if latest_date is None:

                    data = ticker_obj.history(
                        period=period,
                        auto_adjust=True
                    )

                else:

                    start = (
                        pd.to_datetime(latest_date)
                        + pd.Timedelta(days=1)
                    ).strftime("%Y-%m-%d")

                    data = ticker_obj.history(
                        start=start,
                        auto_adjust=True
                    )

                if data.empty:
                    return pd.DataFrame()

                data = data.reset_index()

                data = self.normalize_data(data)

                return data

            except Exception as e:

                print(
                    f"{ticker} 通信失敗 "
                    f"({attempt + 1}/{retry})"
                )

                print(e)

                time.sleep(2)

        return pd.DataFrame()

    def get_stock_list(self):
        """
        Yahoo Financeは銘柄一覧取得に対応していない
        """

        return pd.DataFrame()