import numpy as np
import pandas as pd

from analysis.support_resistance import (
    detect_resistance_lines,
    detect_support_lines,
)


def _build_price_path(control_points, code="7203"):

    """
    指定した(index, value)の点を直線補間して価格系列を作る。
    テスト用にopen=high=low=closeとして単純化する。
    """

    control_indices = [point[0] for point in control_points]
    control_values = [point[1] for point in control_points]

    length = control_indices[-1] + 1

    x = np.arange(length)
    values = np.interp(x, control_indices, control_values)

    return pd.DataFrame({
        "code": [code] * length,
        "date": pd.date_range("2020-01-01", periods=length, freq="D"),
        "open": values,
        "high": values,
        "low": values,
        "close": values,
    })


# 抵抗線100円に、29日目・89日目・149日目の3回タッチする基本パターン
BASE_RESISTANCE = [
    (0, 80),
    (29, 100),
    (59, 80),
    (89, 100),
    (119, 80),
    (149, 100),
    (165, 88),
]


def test_valid_resistance_line_is_detected():
    df = _build_price_path(BASE_RESISTANCE)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert len(lines) == 1
    assert lines[0]["type"] == "resistance"
    assert lines[0]["price"] == 100
    assert lines[0]["touch_count"] == 3


def test_valid_since_date_is_the_third_touch_date():
    df = _build_price_path(BASE_RESISTANCE)

    lines = detect_resistance_lines(df, timeframe="daily")

    # 29,89,149日目の3回タッチ -> 3回目(149日目)が有効化日
    expected_date = pd.date_range("2020-01-01", periods=150, freq="D")[-1]
    assert lines[0]["valid_since_date"] == expected_date


def test_inactivity_reset_excludes_line_even_for_daily_timeframe():
    # 3回タッチ後、365日を超えて反応がないまま横ばいが続く
    control = BASE_RESISTANCE + [(600, 90)]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_touches_outside_lookback_window_are_ignored():
    # 3回のタッチ(10,60,120日目、期間110日)はすべて直近252行より前にある
    control = [
        (0, 80),
        (10, 100),
        (35, 80),
        (60, 100),
        (95, 80),
        (120, 100),
        (140, 88),
        (399, 88),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_touches_within_lookback_window_are_detected():
    # 同じタッチだが、全体の長さが252行未満なのでウィンドウ内に収まる
    control = [
        (0, 80),
        (10, 100),
        (35, 80),
        (60, 100),
        (95, 80),
        (120, 100),
        (140, 88),
        (199, 88),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert len(lines) == 1
    assert lines[0]["price"] == 100


def test_touch_count_below_minimum_excludes_line():
    # タッチが2回だけ
    control = [
        (0, 80),
        (29, 100),
        (59, 80),
        (89, 100),
        (119, 88),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_duration_below_minimum_excludes_line():
    # 3回タッチするが、期間が30日しかない（日足の最低期間90日未満）
    control = [
        (0, 80),
        (5, 100),
        (10, 80),
        (15, 100),
        (20, 80),
        (25, 100),
        (30, 88),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_confirmed_breakout_excludes_line():
    # 基本パターンの後、101円を5日連続で上回る（正式ブレイク）
    control = BASE_RESISTANCE + [
        (166, 105),
        (170, 108),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_single_day_pierce_does_not_exclude_line():
    # 基本パターンの後、1日だけ105円をつけてすぐ90円へ戻る（ダマシ）
    control = BASE_RESISTANCE + [
        (166, 105),
        (167, 90),
        (170, 88),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert len(lines) == 1
    assert lines[0]["price"] == 100


def test_deviation_reset_excludes_line():
    # 基本パターンの後、ブレイクせず緩やかに70円まで乖離する（20%超）
    control = BASE_RESISTANCE + [
        (200, 70),
    ]
    df = _build_price_path(control)

    lines = detect_resistance_lines(df, timeframe="daily")

    assert lines == []


def test_valid_support_line_is_detected():
    # 支持線80円に、29日目・89日目・149日目の3回タッチする基本パターン
    control = [
        (0, 100),
        (29, 80),
        (59, 100),
        (89, 80),
        (119, 100),
        (149, 80),
        (165, 92),
    ]
    df = _build_price_path(control)

    lines = detect_support_lines(df, timeframe="daily")

    assert len(lines) == 1
    assert lines[0]["type"] == "support"
    assert lines[0]["price"] == 80
    assert lines[0]["touch_count"] == 3
