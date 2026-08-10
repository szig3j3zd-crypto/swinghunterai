import pandas as pd

from analysis.ma_cross import detect_perfect_dead_cross, detect_perfect_golden_cross
from analysis.ma_trend import get_ma_slope_series
from config.config import PARALLEL_RISE_OFFSET_DAYS


def detect_parallel_rise(df, direction, offset_days=None, slope_lookback=1):

    """
    並走上昇モジュール判定

    entry_signal_spec.md 6章に対応する。完全ゴールデンクロス（デッドクロス）
    発生日からoffset_days営業日後の日に、MA5がMA20の上（下）で両者とも
    上向き（下向き）を維持していれば、その日を候補日とする。

    Parameters
    ----------
    df
        sma5, sma20 列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    offset_days
        完全ゴールデンクロス（デッドクロス）からの候補日オフセット。
        Noneならconfig.PARALLEL_RISE_OFFSET_DAYSを使う

    Returns
    -------
    result
        各日が並走上昇の候補日かどうかを示すbooleanのSeries
    """

    if offset_days is None:
        offset_days = PARALLEL_RISE_OFFSET_DAYS

    df = df.reset_index(drop=True)
    sma5 = df["sma5"]
    sma20 = df["sma20"]

    slope5 = get_ma_slope_series(sma5, lookback=slope_lookback)
    slope20 = get_ma_slope_series(sma20, lookback=slope_lookback)

    if direction == "long":
        cross_day = detect_perfect_golden_cross(df, slope_lookback=slope_lookback)
        holds = (sma5 > sma20) & (slope5 == "up") & (slope20 == "up")
    elif direction == "short":
        cross_day = detect_perfect_dead_cross(df, slope_lookback=slope_lookback)
        holds = (sma5 < sma20) & (slope5 == "down") & (slope20 == "down")
    else:
        raise ValueError("direction must be 'long' or 'short'")

    candidate = pd.Series(False, index=df.index)

    for pos in df.index[cross_day]:
        target = pos + offset_days

        if target >= len(df):
            continue

        if holds.iloc[target]:
            candidate.iloc[target] = True

    return candidate
