import pandas as pd

from config.config import VOLUME_AVG_WINDOW


def calculate_volume_indicators(df):

    """
    出来高平均・出来高倍率計算
    """

    df = df.copy()


    # 日付統一
    df["date"] = pd.to_datetime(
        df["date"],
        format="mixed",
        utc=True
    )

    # タイムゾーン削除
    df["date"] = df["date"].dt.tz_localize(None)


    # 日付順
    df = df.sort_values(
        ["code", "date"]
    )


    # 出来高平均
    df["volume_avg"] = (
        df["volume"]
        .rolling(window=VOLUME_AVG_WINDOW)
        .mean()
    )

    # 出来高倍率
    df["volume_ratio"] = (
        df["volume"] / df["volume_avg"]
    )


    return df
