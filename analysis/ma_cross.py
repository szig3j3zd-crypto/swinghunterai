def detect_golden_cross(df, short_col, long_col):

    """
    ゴールデンクロス検出

    short_colがlong_colを下から上に抜けた日をTrueとする。

    Parameters
    ----------
    df
        short_col, long_col 列を持つ株価DataFrame（日付順ソート済み）

    short_col
        短期MAの列名（例: "sma5"）

    long_col
        長期MAの列名（例: "sma20"）

    Returns
    -------
    result
        各日がゴールデンクロスかどうかを示すbooleanのSeries
    """

    short = df[short_col]
    long_ = df[long_col]

    return (short.shift(1) <= long_.shift(1)) & (short > long_)


def detect_dead_cross(df, short_col, long_col):

    """
    デッドクロス検出

    short_colがlong_colを上から下に抜けた日をTrueとする。

    Parameters
    ----------
    df
        short_col, long_col 列を持つ株価DataFrame（日付順ソート済み）

    short_col
        短期MAの列名（例: "sma5"）

    long_col
        長期MAの列名（例: "sma20"）

    Returns
    -------
    result
        各日がデッドクロスかどうかを示すbooleanのSeries
    """

    short = df[short_col]
    long_ = df[long_col]

    return (short.shift(1) >= long_.shift(1)) & (short < long_)


def detect_perfect_golden_cross(df, short_col="sma5", long_col="sma20", slope_lookback=1):

    """
    完全ゴールデンクロス検出

    entry_signal_spec.md 4章の「くちばし」型ゴールデンクロス。
    通常のゴールデンクロスに加え、クロス当日のlong_colの傾きがプラス
    （すでに上向きの長期線を短期線が追い抜いていく形）であることを求める。

    Parameters
    ----------
    df
        short_col, long_col 列を持つ株価DataFrame（日付順ソート済み）

    Returns
    -------
    result
        各日が完全ゴールデンクロスかどうかを示すbooleanのSeries
    """

    cross = detect_golden_cross(df, short_col, long_col)
    long_slope_up = df[long_col] > df[long_col].shift(slope_lookback)

    return cross & long_slope_up


def detect_perfect_dead_cross(df, short_col="sma5", long_col="sma20", slope_lookback=1):

    """
    完全デッドクロス検出（完全ゴールデンクロスの逆）

    通常のデッドクロスに加え、クロス当日のlong_colの傾きがマイナスで
    あることを求める。

    Parameters
    ----------
    df
        short_col, long_col 列を持つ株価DataFrame（日付順ソート済み）

    Returns
    -------
    result
        各日が完全デッドクロスかどうかを示すbooleanのSeries
    """

    cross = detect_dead_cross(df, short_col, long_col)
    long_slope_down = df[long_col] < df[long_col].shift(slope_lookback)

    return cross & long_slope_down
