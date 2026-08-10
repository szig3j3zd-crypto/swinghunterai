import pandas as pd

from analysis.half_signal import detect_half_signal


def test_long_fires_when_body_midpoint_crosses_above_sma5():
    # row0: 実体中央値(95) < sma5(100) -> 不成立
    # row1: 実体中央値(105) >= sma5(100) -> 成立（遷移日）
    df = pd.DataFrame({
        "open": [95, 105],
        "close": [95, 105],
        "sma5": [100, 100],
    })

    result = detect_half_signal(df, direction="long")

    assert list(result["half_signal"]) == [False, True]


def test_long_does_not_fire_when_sma5_slope_is_down():
    # 実体中央値はsma5を上回るが、sma5自体の傾きがマイナスのため前提条件を満たさない
    df = pd.DataFrame({
        "open": [105, 106],
        "close": [105, 106],
        "sma5": [110, 100],
    })

    result = detect_half_signal(df, direction="long")

    assert list(result["half_signal"]) == [False, False]


def test_long_only_transition_day_fires_not_every_day_in_state():
    # row1・row2とも実体中央値がsma5以上だが、遷移日（row1）のみがTrue
    df = pd.DataFrame({
        "open": [95, 105, 106],
        "close": [95, 105, 106],
        "sma5": [100, 100, 101],
    })

    result = detect_half_signal(df, direction="long")

    assert list(result["half_signal"]) == [False, True, False]


def test_long_whole_body_above_sma5_also_counts():
    # 実体全体がsma5より上にある場合も、実体中央値がsma5以上の条件に含まれる
    df = pd.DataFrame({
        "open": [95, 108],
        "close": [95, 112],
        "sma5": [100, 100],
    })

    result = detect_half_signal(df, direction="long")

    assert list(result["half_signal"]) == [False, True]


def test_short_fires_when_body_midpoint_crosses_below_sma5():
    df = pd.DataFrame({
        "open": [105, 95],
        "close": [105, 95],
        "sma5": [100, 100],
    })

    result = detect_half_signal(df, direction="short")

    assert list(result["half_signal"]) == [False, True]


def test_short_does_not_fire_when_sma5_slope_is_up():
    df = pd.DataFrame({
        "open": [95, 94],
        "close": [95, 94],
        "sma5": [90, 100],
    })

    result = detect_half_signal(df, direction="short")

    assert list(result["half_signal"]) == [False, False]
