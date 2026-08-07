import pandas as pd

from analysis.ma_cross import detect_dead_cross, detect_golden_cross


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
