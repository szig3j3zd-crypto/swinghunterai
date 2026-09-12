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

        全リトライが通信失敗で尽きた場合は最後の例外をそのまま送出する
        （2026-09-13改訂。以前は空のDataFrameを返しており、「新しいデータ
        なし（既に最新）」という正常な結果と区別できなかった。呼び出し元の
        ProviderManagerがこれを"取得失敗"とみなして毎回J-Quantsへも
        フォールバックしてしまい、既に最新の銘柄1つ1つに対して常に無駄な
        API呼び出しが発生し、全銘柄更新が不必要に遅くなっていたため）
        """

        ticker_obj = yf.Ticker(ticker)

        last_error = None

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

                last_error = e

                print(
                    f"{ticker} 通信失敗 "
                    f"({attempt + 1}/{retry})"
                )

                print(e)

                time.sleep(2)

        raise last_error

    def get_stock_list(self):
        """
        Yahoo Financeは銘柄一覧取得に対応していない
        """

        return pd.DataFrame()