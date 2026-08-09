import pandas as pd


def detect_half_signal(df, direction, support_price=None, resistance_price=None):

    """
    半分シグナル判定

    docs/specifications/entry_signal_spec.md 4章に対応する。

    パターンA: 支持線/抵抗線付近での半分シグナル
    パターンB: 5日線・20日線のゴールデンクロス／デッドクロス（優先度高）

    Parameters
    ----------
    df
        open, close, sma5, sma20, sma60 列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    support_price
        直近の支持線価格（ロング判定のパターンA用。Noneならパターンaを評価しない）

    resistance_price
        直近の抵抗線価格（ショート判定のパターンA用。Noneならパターンaを評価しない）

    Returns
    -------
    result
        half_signal（bool）, pattern（"A" | "B" | None）を持つDataFrame
    """

    if direction == "long":
        pattern_b = _crossed_sma5_above_sma20(df)

        if support_price is not None:
            pattern_a = (
                _crossed_above_sma5(df)
                & (df["close"] > support_price)
                & (df["close"] > df["sma60"])
            )
        else:
            pattern_a = pd.Series(False, index=df.index)

    elif direction == "short":
        pattern_b = _crossed_sma5_below_sma20(df)

        if resistance_price is not None:
            pattern_a = (
                _crossed_below_sma5(df)
                & (df["close"] < resistance_price)
                & (df["close"] < df["sma60"])
            )
        else:
            pattern_a = pd.Series(False, index=df.index)

    else:
        raise ValueError("direction must be 'long' or 'short'")

    pattern = pd.Series(None, index=df.index, dtype=object)
    pattern[pattern_a] = "A"
    pattern[pattern_b] = "B"

    return pd.DataFrame({
        "half_signal": pattern_a | pattern_b,
        "pattern": pattern,
    })


def _candle_body_midpoint(df):

    """
    ローソク足実体の中央値
    """

    return (df["open"] + df["close"]) / 2


def _crossed_above_sma5(df):

    """
    実体の中央値が5日線を下から上に抜けた日
    """

    midpoint = _candle_body_midpoint(df)

    return (midpoint.shift(1) <= df["sma5"].shift(1)) & (midpoint > df["sma5"])


def _crossed_below_sma5(df):

    """
    実体の中央値が5日線を上から下に抜けた日
    """

    midpoint = _candle_body_midpoint(df)

    return (midpoint.shift(1) >= df["sma5"].shift(1)) & (midpoint < df["sma5"])


def _crossed_sma5_above_sma20(df):

    """
    5日線が20日線を下から上に抜けた日（ゴールデンクロス）
    """

    return (df["sma5"].shift(1) <= df["sma20"].shift(1)) & (df["sma5"] > df["sma20"])


def _crossed_sma5_below_sma20(df):

    """
    5日線が20日線を上から下に抜けた日（デッドクロス）
    """

    return (df["sma5"].shift(1) >= df["sma20"].shift(1)) & (df["sma5"] < df["sma20"])
