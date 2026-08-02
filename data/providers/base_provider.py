from abc import ABC, abstractmethod

import pandas as pd


class BaseProvider(ABC):
    """
    データ取得Provider基底クラス
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider名
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        利用可能か判定
        """
        pass

    @abstractmethod
    def get_stock_data(
        self,
        ticker: str,
        latest_date=None
    ) -> pd.DataFrame:
        """
        株価取得
        """
        pass

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """
        銘柄一覧取得

        対応していないProviderは
        空のDataFrameを返す。
        """
        pass

    def normalize_data(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Providerごとの差異を吸収する。

        戻り値は必ず

        Date
        Open
        High
        Low
        Close
        Volume

        の6列とする。
        """

        if df.empty:
            return df

        rename_map = {}

        if "Adj Open" in df.columns:
            rename_map["Adj Open"] = "Open"

        if "Adj High" in df.columns:
            rename_map["Adj High"] = "High"

        if "Adj Low" in df.columns:
            rename_map["Adj Low"] = "Low"

        if "Adj Close" in df.columns:
            rename_map["Adj Close"] = "Close"

        if "Adj Volume" in df.columns:
            rename_map["Adj Volume"] = "Volume"

        df = df.rename(columns=rename_map)

        columns = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        return df[columns]