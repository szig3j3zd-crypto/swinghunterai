import pandas as pd


def calculate_moving_average(df):

    """
    移動平均線計算
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


    # 移動平均
    df["sma5"] = (
        df["close"]
        .rolling(window=5)
        .mean()
    )

    df["sma25"] = (
        df["close"]
        .rolling(window=25)
        .mean()
    )

    df["sma75"] = (
        df["close"]
        .rolling(window=75)
        .mean()
    )


    return df