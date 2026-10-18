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

    # resample()のインデックスは暦上の周期境界（週足なら週末の日曜、
    # 月足なら月末）で、その週・月の最後の実際の取引日とは一致しない
    # （祝日・週末や月の途中までしかデータが無い場合は特にずれる）。
    # チャートの「一番右（最新）の日付」を日足/週足/月足で揃えるため、
    # 境界日ではなくその周期内に実在する最後の取引日を"date"列として使う
    # （2026-10-18修正。"date"をインデックスとは別に通常の列としても
    # 残しておき、集計時に"last"でその周期内の最後の実データ日を拾う）
    df["_last_trading_date"] = df["date"]

    resampled = (
        df
        .set_index("date")
        .groupby("code")
        .resample(rule)
        .agg({
            "_last_trading_date": "last",
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        })
        .dropna(subset=["open"])
        .reset_index()
        .drop(columns=["date"])
        .rename(columns={"_last_trading_date": "date"})
    )

    return resampled[["code", "date", "open", "high", "low", "close", "volume"]]


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
