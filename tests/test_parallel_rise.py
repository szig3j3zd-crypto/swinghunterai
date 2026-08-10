import pandas as pd

from analysis.parallel_rise import detect_parallel_rise


def test_candidate_two_business_days_after_perfect_golden_cross():
    # index2で完全ゴールデンクロスが発生し、2営業日後のindex4で
    # MA5>MA20・両MA上向きを維持している
    df = pd.DataFrame({
        "sma5": [9.0, 9.8, 10.6, 11.0, 11.5],
        "sma20": [10.0, 10.2, 10.5, 10.8, 11.1],
    })

    result = detect_parallel_rise(df, direction="long")

    assert list(result) == [False, False, False, False, True]


def test_no_candidate_when_state_fails_at_offset_day():
    # index2で完全ゴールデンクロスは発生するが、index4でMA5がMA20を割り込む
    df = pd.DataFrame({
        "sma5": [9.0, 9.8, 10.6, 11.0, 10.5],
        "sma20": [10.0, 10.2, 10.5, 10.8, 11.1],
    })

    result = detect_parallel_rise(df, direction="long")

    assert not result.any()


def test_no_candidate_when_no_perfect_golden_cross():
    df = pd.DataFrame({
        "sma5": [9.0, 9.2, 9.4, 9.6, 9.8],
        "sma20": [10.0, 10.2, 10.5, 10.8, 11.1],
    })

    result = detect_parallel_rise(df, direction="long")

    assert not result.any()


def test_short_candidate_two_business_days_after_perfect_dead_cross():
    df = pd.DataFrame({
        "sma5": [11.0, 10.2, 9.4, 9.0, 8.5],
        "sma20": [10.0, 9.8, 9.5, 9.2, 8.9],
    })

    result = detect_parallel_rise(df, direction="short")

    assert list(result) == [False, False, False, False, True]
