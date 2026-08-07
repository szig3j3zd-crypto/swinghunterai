import pandas as pd

from analysis.swing_points import detect_swing_highs, detect_swing_lows


def _series(column, values):
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=len(values), freq="D"),
        column: values,
    })


def test_detect_swing_highs_finds_single_peak():
    # 1,2,3 と上昇し10でピーク、その後10,9,...,3と単調減少
    values = [1, 2, 3, 10, 9, 8, 7, 6, 5, 4, 3]
    df = _series("high", values)

    result = detect_swing_highs(df, window=2)

    assert len(result) == 1
    assert result.iloc[0]["price"] == 10
    assert result.iloc[0]["date"] == pd.Timestamp("2026-01-04")


def test_detect_swing_lows_finds_single_trough():
    # 10,9,8 と下降し1で底、その後1,2,...,8と単調増加
    values = [10, 9, 8, 1, 2, 3, 4, 5, 6, 7, 8]
    df = _series("low", values)

    result = detect_swing_lows(df, window=2)

    assert len(result) == 1
    assert result.iloc[0]["price"] == 1
    assert result.iloc[0]["date"] == pd.Timestamp("2026-01-04")


def test_boundary_values_are_not_detected_as_swing_high():
    # 先頭が最大値でも、左側の比較対象が無いので候補にならない
    values = [100, 1, 2, 3, 4]
    df = _series("high", values)

    result = detect_swing_highs(df, window=2)

    assert len(result) == 0
