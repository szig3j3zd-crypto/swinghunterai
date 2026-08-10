import pandas as pd

from analysis.ma_trend import get_ma_slope_series


def detect_half_signal(df, direction, slope_lookback=1):

    """
    半分シグナル判定（2026-08改訂）

    entry_signal_spec.md 7章に対応する。ローソク足実体（始値・終値）の
    中央値がMA5をどれだけ上抜けているかで判定する。

    旧パターンA（支持線付近での半分シグナル）・旧パターンB（5日線・20日線の
    ゴールデンクロス）は廃止。完全ゴールデンクロスはanalysis/ma_cross.pyの
    detect_perfect_golden_cross/detect_perfect_dead_crossへ移動した。

    Parameters
    ----------
    df
        open, close, sma5 列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    Returns
    -------
    result
        half_signal（bool）を持つDataFrame。前日は不成立→当日成立の
        遷移日のみをTrueとする
    """

    midpoint = (df["open"] + df["close"]) / 2
    slope5 = get_ma_slope_series(df["sma5"], lookback=slope_lookback)

    if direction == "long":
        above = midpoint >= df["sma5"]
        slope_ok = slope5 != "down"
    elif direction == "short":
        above = midpoint <= df["sma5"]
        slope_ok = slope5 != "up"
    else:
        raise ValueError("direction must be 'long' or 'short'")

    state = (above & slope_ok).astype(bool)
    half_signal = state & ~state.shift(1, fill_value=False)

    return pd.DataFrame({"half_signal": half_signal})
