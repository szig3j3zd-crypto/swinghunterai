import pandas as pd


class DataValidator:
    """
    株価データ検証
    """

    REQUIRED_COLUMNS = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    @classmethod
    def validate(cls, data: pd.DataFrame):

        if data is None:

            return False


        # 必須列
        for column in cls.REQUIRED_COLUMNS:

            if column not in data.columns:

                print(f"{column}列なし")

                return False

        # 欠損
        if data[cls.REQUIRED_COLUMNS].isnull().any().any():

            print("欠損あり")

            return False

        # 日付重複
        if data["Date"].duplicated().any():

            print("日付重複")

            return False

        # 昇順

        if not data["Date"].is_monotonic_increasing:

            print("日付順エラー")

            return False

        return True