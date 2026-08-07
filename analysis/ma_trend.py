import pandas as pd


def get_ma_order_series(df):

    """
    日ごとのMA5/MA20/MA60の並び順を判定する

    Parameters
    ----------
    df
        sma5, sma20, sma60 列を持つ株価DataFrame（日付順ソート済み）

    Returns
    -------
    order
        "long"（5>20>60） | "short"（60>20>5） | "mixed"（どちらでもない）
        を各日について持つSeries
    """

    is_long = (df["sma5"] > df["sma20"]) & (df["sma20"] > df["sma60"])
    is_short = (df["sma60"] > df["sma20"]) & (df["sma20"] > df["sma5"])

    order = pd.Series("mixed", index=df.index)
    order[is_long] = "long"
    order[is_short] = "short"

    return order


def get_ma_slope_series(series, lookback=1):

    """
    日ごとの傾き方向を判定する

    Parameters
    ----------
    series
        MAのSeries（日付順ソート済み）

    lookback
        何日前の値と比較するか

    Returns
    -------
    slope
        "up" | "down" | "flat" | None（比較対象が無い先頭部分）
        を各日について持つSeries
    """

    diff = series - series.shift(lookback)

    slope = pd.Series("flat", index=series.index, dtype=object)
    slope[diff > 0] = "up"
    slope[diff < 0] = "down"
    slope[diff.isna()] = None

    return slope


def is_long_trend_series(df, slope_lookback=1):

    """
    日ごとのロング（上昇トレンド）判定

    上から5>20>60の順で並び、かつ各MAが上向きであること。
    """

    order = get_ma_order_series(df)

    slopes_up = pd.Series(True, index=df.index)

    for column in ("sma5", "sma20", "sma60"):
        slope = get_ma_slope_series(df[column], lookback=slope_lookback)
        slopes_up &= (slope == "up")

    return (order == "long") & slopes_up


def is_short_trend_series(df, slope_lookback=1):

    """
    日ごとのショート（下降トレンド）判定

    上から60>20>5の順で並び、かつ各MAが下向きであること。
    """

    order = get_ma_order_series(df)

    slopes_down = pd.Series(True, index=df.index)

    for column in ("sma5", "sma20", "sma60"):
        slope = get_ma_slope_series(df[column], lookback=slope_lookback)
        slopes_down &= (slope == "down")

    return (order == "short") & slopes_down


def get_ma_order(df):

    """
    直近日のMA5/MA20/MA60の並び順を判定する

    Returns
    -------
    order
        "long"（5>20>60） | "short"（60>20>5） | "mixed"（どちらでもない）
    """

    return get_ma_order_series(df).iloc[-1]


def get_ma_slope(series, lookback=1):

    """
    直近の傾き方向を判定する

    Returns
    -------
    slope
        "up" | "down" | "flat"
    """

    return get_ma_slope_series(series, lookback=lookback).iloc[-1]


def is_long_trend(df, slope_lookback=1):

    """
    直近日のロング（上昇トレンド）判定
    """

    return bool(is_long_trend_series(df, slope_lookback=slope_lookback).iloc[-1])


def is_short_trend(df, slope_lookback=1):

    """
    直近日のショート（下降トレンド）判定
    """

    return bool(is_short_trend_series(df, slope_lookback=slope_lookback).iloc[-1])


def get_current_trend_period(df, direction, slope_lookback=1):

    """
    直近まで連続しているトレンド期間の開始日を取得する

    Parameters
    ----------
    df
        date, sma5, sma20, sma60 列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    Returns
    -------
    start_date
        直近まで連続してトレンド条件を満たしている期間の開始日。
        直近日がトレンド中でなければNone
    """

    if direction == "long":
        trend = is_long_trend_series(df, slope_lookback=slope_lookback)
    elif direction == "short":
        trend = is_short_trend_series(df, slope_lookback=slope_lookback)
    else:
        raise ValueError("direction must be 'long' or 'short'")

    trend = trend.reset_index(drop=True)

    if not trend.iloc[-1]:
        return None

    position = len(trend) - 1

    while position > 0 and trend.iloc[position - 1]:
        position -= 1

    return df["date"].reset_index(drop=True).iloc[position]
