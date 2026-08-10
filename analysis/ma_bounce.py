import pandas as pd

from analysis.ma_trend import get_ma_slope_series
from config.config import (
    BOUNCE_MA_PROXIMITY_PCT,
    BOUNCE_MIN_DECLINE_DAYS,
    BOUNCE_UNDERSHOOT_RECOVERY_DAYS,
)


def detect_bounce(df, direction, min_decline_days=None, proximity_pct=None,
                   undershoot_recovery_days=None, slope_lookback=1):

    """
    反発モジュール判定

    entry_signal_spec.md 5章に対応する。MA5がMA20に接近したときの
    反発挙動（MA20を下回らない反発／MA20を少し下回ってからの反発）を検出する。

    Parameters
    ----------
    df
        sma5, sma20 列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    min_decline_days
        反発の前提となる、直前のMA5下向き（ロング）/上向き（ショート）継続の
        最低営業日数。Noneならconfig.BOUNCE_MIN_DECLINE_DAYSを使う

    proximity_pct
        MA5とMA20の接近しきい値（乖離率）。Noneならconfig.BOUNCE_MA_PROXIMITY_PCTを使う

    undershoot_recovery_days
        MA20を下回ってから回復とみなす猶予営業日数。
        Noneならconfig.BOUNCE_UNDERSHOOT_RECOVERY_DAYSを使う

    Returns
    -------
    result
        bounce_candidate（エントリー候補日）、bounce_watch（監視銘柄として
        出力する日）を持つDataFrame
    """

    if min_decline_days is None:
        min_decline_days = BOUNCE_MIN_DECLINE_DAYS

    if proximity_pct is None:
        proximity_pct = BOUNCE_MA_PROXIMITY_PCT

    if undershoot_recovery_days is None:
        undershoot_recovery_days = BOUNCE_UNDERSHOOT_RECOVERY_DAYS

    df = df.reset_index(drop=True)
    sma5 = df["sma5"]
    sma20 = df["sma20"]

    slope5 = get_ma_slope_series(sma5, lookback=slope_lookback)
    slope20 = get_ma_slope_series(sma20, lookback=slope_lookback)

    if direction == "long":
        decline_state = "down"
        reversal_to = "up"
        ma20_precondition = "up"
        correct_side = sma5 >= sma20
    elif direction == "short":
        decline_state = "up"
        reversal_to = "down"
        ma20_precondition = "down"
        correct_side = sma5 <= sma20
    else:
        raise ValueError("direction must be 'long' or 'short'")

    is_decline = slope5 == decline_state
    group = (is_decline != is_decline.shift()).cumsum()
    decline_streak = is_decline.groupby(group).cumcount() + 1
    decline_streak = decline_streak.where(is_decline, 0)

    decline_ok = decline_streak.shift(1).fillna(0) >= min_decline_days

    reversal_day = (slope5.shift(1) == decline_state) & (slope5 == reversal_to)

    diff_pct = (sma5 - sma20).abs() / sma20
    within_proximity = diff_pct <= proximity_pct

    ma20_ok = slope20 == ma20_precondition

    candidate = pd.Series(False, index=df.index)
    watch = pd.Series(False, index=df.index)

    trigger_positions = df.index[reversal_day & decline_ok & ma20_ok & within_proximity]

    for pos in trigger_positions:

        if correct_side.iloc[pos]:
            candidate.iloc[pos] = True
            continue

        watch.iloc[pos] = True

        for offset in range(1, undershoot_recovery_days + 1):
            check_pos = pos + offset

            if check_pos >= len(df):
                break

            if correct_side.iloc[check_pos]:
                candidate.iloc[check_pos] = True
                break

            if not within_proximity.iloc[check_pos]:
                break

            watch.iloc[check_pos] = True

    return pd.DataFrame({"bounce_candidate": candidate, "bounce_watch": watch})
