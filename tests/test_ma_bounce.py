import pandas as pd

from analysis.ma_bounce import detect_bounce


def test_case1_no_undershoot_reversal_is_candidate():
    # sma5がsma20を下回らずに反発するケース（3営業日以上の下落継続後に反転）
    df = pd.DataFrame({
        "sma5": [110, 107, 104, 101.5, 103.0],
        "sma20": [100.0, 100.4, 100.8, 101.2, 102.2],
    })

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_candidate"]) == [False, False, False, False, True]
    assert list(result["bounce_watch"]) == [False, False, False, False, False]


def test_case2_undershoot_recovers_within_window():
    # sma5がsma20を少し下回ってから、翌営業日に回復するケース
    df = pd.DataFrame({
        "sma5": [110, 107, 104, 101.5, 102.0, 103.0],
        "sma20": [100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    })

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_watch"]) == [False, False, False, False, True, False]
    assert list(result["bounce_candidate"]) == [False, False, False, False, False, True]


def test_case2_undershoot_without_recovery_stays_watch_only():
    # sma5がsma20を下回った後、乖離が広がってしまい反発不成立になるケース
    df = pd.DataFrame({
        "sma5": [110, 107, 104, 101.5, 102.0, 95.0],
        "sma20": [100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    })

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_watch"]) == [False, False, False, False, True, False]
    assert list(result["bounce_candidate"]) == [False, False, False, False, False, False]


def test_short_case1_no_overshoot_reversal_is_candidate():
    # ショート版: sma5がsma20を上回らずに反発する（下落トレンドへの反転）
    df = pd.DataFrame({
        "sma5": [90, 93, 96, 98.5, 97.0],
        "sma20": [100.0, 99.6, 99.2, 98.8, 97.8],
    })

    result = detect_bounce(df, direction="short")

    assert list(result["bounce_candidate"]) == [False, False, False, False, True]
    assert list(result["bounce_watch"]) == [False, False, False, False, False]


def test_short_case2_overshoot_recovers_within_window():
    # ショート版: sma5がsma20を少し上回ってから、翌営業日に回復(下回る)するケース
    df = pd.DataFrame({
        "sma5": [90, 93, 96, 98.5, 98.0, 97.0],
        "sma20": [100.0, 99.6, 99.2, 98.8, 97.8, 97.4],
    })

    result = detect_bounce(df, direction="short")

    assert list(result["bounce_watch"]) == [False, False, False, False, True, False]
    assert list(result["bounce_candidate"]) == [False, False, False, False, False, True]


def test_no_trigger_when_precondition_not_met():
    # 下落継続が2営業日しかないため、反発の前提条件を満たさない
    df = pd.DataFrame({
        "sma5": [110, 107, 104, 106.0],
        "sma20": [100.0, 100.4, 100.8, 101.2],
    })

    result = detect_bounce(df, direction="long")

    assert not result["bounce_candidate"].any()
    assert not result["bounce_watch"].any()
