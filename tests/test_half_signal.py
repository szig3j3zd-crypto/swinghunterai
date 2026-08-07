import pandas as pd

from analysis.half_signal import detect_half_signal


def _long_df(sma20, sma60):
    # row0: 実体中央値(95) <= sma5(100) -> 未クロス
    # row1: 実体中央値(105) > sma5(100) -> クロス
    return pd.DataFrame({
        "open": [95, 105],
        "close": [95, 105],
        "sma5": [100, 100],
        "sma20": sma20,
        "sma60": sma60,
    })


def test_pattern_b_fires_when_above_sma20():
    df = _long_df(sma20=[90, 90], sma60=[80, 80])

    result = detect_half_signal(df, direction="long")

    assert list(result["half_signal"]) == [False, True]
    assert result["pattern"].iloc[1] == "B"


def test_pattern_a_fires_when_above_support_and_sma60():
    # close(105) < sma20(110) なのでパターンBは発火しない
    df = _long_df(sma20=[110, 110], sma60=[80, 80])

    result = detect_half_signal(df, direction="long", support_price=100)

    assert list(result["half_signal"]) == [False, True]
    assert result["pattern"].iloc[1] == "A"


def test_pattern_b_takes_priority_when_both_fire():
    df = _long_df(sma20=[90, 90], sma60=[80, 80])

    result = detect_half_signal(df, direction="long", support_price=50)

    assert result["pattern"].iloc[1] == "B"


def test_no_signal_when_neither_condition_holds():
    df = _long_df(sma20=[110, 110], sma60=[120, 120])

    result = detect_half_signal(df, direction="long", support_price=200)

    assert list(result["half_signal"]) == [False, False]


def test_short_pattern_b_fires_when_below_sma20():
    # row0: 実体中央値(105) >= sma5(100) -> 未クロス
    # row1: 実体中央値(95) < sma5(100) -> クロス
    df = pd.DataFrame({
        "open": [105, 95],
        "close": [105, 95],
        "sma5": [100, 100],
        "sma20": [110, 110],
        "sma60": [120, 120],
    })

    result = detect_half_signal(df, direction="short")

    assert list(result["half_signal"]) == [False, True]
    assert result["pattern"].iloc[1] == "B"


def test_short_pattern_a_fires_when_below_resistance_and_sma60():
    # close(95) > sma20(90) なのでパターンBは発火しない
    df = pd.DataFrame({
        "open": [105, 95],
        "close": [105, 95],
        "sma5": [100, 100],
        "sma20": [90, 90],
        "sma60": [120, 120],
    })

    result = detect_half_signal(df, direction="short", resistance_price=100)

    assert list(result["half_signal"]) == [False, True]
    assert result["pattern"].iloc[1] == "A"
