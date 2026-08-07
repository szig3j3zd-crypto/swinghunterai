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
