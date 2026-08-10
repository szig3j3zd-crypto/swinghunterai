import pandas as pd

from analysis.ma_cross import (
    detect_dead_cross,
    detect_golden_cross,
    detect_perfect_dead_cross,
    detect_perfect_golden_cross,
)


def test_detect_golden_cross_flags_the_crossing_day():
    df = pd.DataFrame({
        "short": [8, 9, 11, 12],
        "long": [10, 10, 10, 10],
    })

    result = detect_golden_cross(df, "short", "long")

    assert list(result) == [False, False, True, False]


def test_detect_dead_cross_flags_the_crossing_day():
    df = pd.DataFrame({
        "short": [12, 11, 9, 8],
        "long": [10, 10, 10, 10],
    })

    result = detect_dead_cross(df, "short", "long")

    assert list(result) == [False, False, True, False]


def test_no_cross_returns_all_false():
    df = pd.DataFrame({
        "short": [12, 13, 14, 15],
        "long": [10, 10, 10, 10],
    })

    result = detect_golden_cross(df, "short", "long")

    assert not result.any()


def test_perfect_golden_cross_requires_long_col_slope_up():
    df = pd.DataFrame({
        "short": [8, 9, 11, 12],
        "long": [11, 10, 10.5, 10.5],
    })

    result = detect_perfect_golden_cross(df, "short", "long")

    # クロスはrow2で発生するが、long列の傾きは10->10.5でプラスのため成立する
    assert list(result) == [False, False, True, False]


def test_perfect_golden_cross_fails_when_long_col_flat_or_down():
    df = pd.DataFrame({
        "short": [8, 9, 11, 12],
        "long": [10, 10, 10, 10],
    })

    result = detect_perfect_golden_cross(df, "short", "long")

    # 通常のゴールデンクロスは発生するが、long列（20日線）の傾きが横ばいのため不成立
    assert not result.any()


def test_perfect_dead_cross_requires_long_col_slope_down():
    df = pd.DataFrame({
        "short": [12, 11, 9, 8],
        "long": [9, 10, 9.5, 9.5],
    })

    result = detect_perfect_dead_cross(df, "short", "long")

    assert list(result) == [False, False, True, False]


def test_perfect_dead_cross_fails_when_long_col_flat_or_up():
    df = pd.DataFrame({
        "short": [12, 11, 9, 8],
        "long": [10, 10, 10, 10],
    })

    result = detect_perfect_dead_cross(df, "short", "long")

    assert not result.any()
