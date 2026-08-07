import pandas as pd


def resample_ohlcv(df, rule):

    """
    日足OHLCVを指定周期へリサンプル

    Parameters
    ----------
    df
        日足の株価DataFrame（code, date, open, high, low, close, volume）

    rule
        pandasのresampleルール（週足="W", 月足="ME"）

    Returns
    -------
    resampled
        銘柄ごとにリサンプルされたOHLCV DataFrame
    """

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        format="mixed",
        utc=True
    )

    df["date"] = df["date"].dt.tz_localize(None)

    df = df.sort_values(
        ["code", "date"]
    )

    resampled = (
        df
        .set_index("date")
        .groupby("code")
        .resample(rule)
        .agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        .dropna(subset=["open"])
        .reset_index()
    )

    return resampled


def resample_to_weekly(df):

    """
    週足へリサンプル
    """

    return resample_ohlcv(df, "W")


def resample_to_monthly(df):

    """
    月足へリサンプル
    """

    return resample_ohlcv(df, "ME")
