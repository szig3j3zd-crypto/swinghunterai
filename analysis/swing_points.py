import pandas as pd


def detect_swing_highs(df, window=2):

    """
    スイングハイ（局所的な高値）検出

    前後window本より高い足を高値候補とする。

    Parameters
    ----------
    df
        date, high 列を持つ株価DataFrame（単一銘柄、日付順ソート済み）

    window
        前後何本と比較するか

    Returns
    -------
    points
        高値候補（date, price）のDataFrame
    """

    df = df.sort_values("date").reset_index(drop=True)

    is_swing_high = pd.Series(True, index=df.index)

    for shift in range(1, window + 1):
        is_swing_high &= df["high"] > df["high"].shift(shift)
        is_swing_high &= df["high"] > df["high"].shift(-shift)

    points = (
        df.loc[is_swing_high, ["date", "high"]]
        .rename(columns={"high": "price"})
        .reset_index(drop=True)
    )

    return points


def detect_swing_lows(df, window=2):

    """
    スイングロー（局所的な安値）検出

    前後window本より安い足を安値候補とする。

    Parameters
    ----------
    df
        date, low 列を持つ株価DataFrame（単一銘柄、日付順ソート済み）

    window
        前後何本と比較するか

    Returns
    -------
    points
        安値候補（date, price）のDataFrame
    """

    df = df.sort_values("date").reset_index(drop=True)

    is_swing_low = pd.Series(True, index=df.index)

    for shift in range(1, window + 1):
        is_swing_low &= df["low"] < df["low"].shift(shift)
        is_swing_low &= df["low"] < df["low"].shift(-shift)

    points = (
        df.loc[is_swing_low, ["date", "low"]]
        .rename(columns={"low": "price"})
        .reset_index(drop=True)
    )

    return points
