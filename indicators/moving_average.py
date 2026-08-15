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
    df["sma3"] = (
        df["close"]
        .rolling(window=3)
        .mean()
    )

    df["sma5"] = (
        df["close"]
        .rolling(window=5)
        .mean()
    )

    df["sma7"] = (
        df["close"]
        .rolling(window=7)
        .mean()
    )

    df["sma10"] = (
        df["close"]
        .rolling(window=10)
        .mean()
    )

    df["sma20"] = (
        df["close"]
        .rolling(window=20)
        .mean()
    )

    df["sma60"] = (
        df["close"]
        .rolling(window=60)
        .mean()
    )

    df["sma100"] = (
        df["close"]
        .rolling(window=100)
        .mean()
    )

    # 超長期線（トレンド判定には使用しない参考指標。表示切替はUI層でSHOW_MA300を参照）
    df["sma300"] = (
        df["close"]
        .rolling(window=300)
        .mean()
    )


    return df