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

        df = df[columns]

        # 最新日（まだ取引が確定していない日）の行はOHLCがNaNのまま返って
        # くることがある（2026-10-28発見・修正。プライム市場の過去データ
        # 拡張取得でperiod="max"を使うようにした結果、1,478銘柄中971銘柄が
        # 「欠損あり」でデータ検証に失敗していた。原因を調べたところ、
        # ほぼ全件が「取得した数千行のうち、末尾の最新日1行だけがNaN」
        # という同じパターンだった。DataValidatorは1行でもNaNがあると
        # データ全体を不採用にする作りのため、何年分もの正常な過去データが
        # この末尾1行のせいで丸ごと捨てられていた）。この1行を落としておく
        # ことで、それ以外の正常な行はそのまま使えるようにする
        return df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])