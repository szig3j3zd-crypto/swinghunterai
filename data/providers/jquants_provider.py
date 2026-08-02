import pandas as pd

from jquantsapi import ClientV2

from config.settings import JQUANTS_API_KEY
from data.providers.base_provider import BaseProvider


class JQuantsProvider(BaseProvider):
    """
    J-Quants Provider
    """

    @property
    def name(self):
        return "J-Quants"

    def is_available(self):
        """
        APIキーが設定されていれば利用可能
        """
        return JQUANTS_API_KEY != ""

    def get_stock_data(
        self,
        ticker,
        latest_date=None,
        period="1y"
    ):
        """
        株価取得
        """

        code = ticker.replace(".T", "")

        client = ClientV2(
            api_key=JQUANTS_API_KEY
        )

        df = client.get_eq_bars_daily(
            code=code
        )

        if df is None or df.empty:
            return pd.DataFrame()

        result = pd.DataFrame()

        result["Date"] = pd.to_datetime(df["Date"])

        result["Open"] = df["AdjO"].fillna(df["O"])
        result["High"] = df["AdjH"].fillna(df["H"])
        result["Low"] = df["AdjL"].fillna(df["L"])
        result["Close"] = df["AdjC"].fillna(df["C"])
        result["Volume"] = df["AdjVo"].fillna(df["Vo"])

        # OHLCが全部Noneの行は除外
        result = result.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ],
            how="all"
        )

        if latest_date is not None:

            latest = pd.to_datetime(latest_date)

            result = result[
                result["Date"] > latest
            ]

        result = result.reset_index(drop=True)

        return result

    def get_stock_list(self):
        """
        上場銘柄一覧取得
        """

        client = ClientV2(
            api_key=JQUANTS_API_KEY
        )

        df = client.get_eq_master()

        if df is None or df.empty:
            return pd.DataFrame()

        return df.reset_index(drop=True)