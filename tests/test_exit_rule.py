import pandas as pd

from rules.exit_rule import (
    calculate_risk_reward_ratio,
    get_previous_swing_high,
    get_previous_swing_low,
    get_round_level_above,
    get_round_level_below,
    get_stop_loss_price,
    get_take_profit_price,
)


def _high_df(values):
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=len(values), freq="D"),
        "high": values,
    })


def _low_df(values, sma20_last):
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=len(values), freq="D"),
        "low": values,
        "sma20": [sma20_last] * len(values),
    })
    return df


def test_round_level_above_matches_example_from_spec():
    # 3000円の次の節目は3500円
    assert get_round_level_above(3000) == 3500


def test_round_level_below_matches_example_from_spec():
    assert get_round_level_below(3200) == 3000


def test_round_step_scales_with_price_magnitude():
    assert get_round_level_above(500) == 600       # 100円刻み
    assert get_round_level_above(3000) == 3500      # 500円刻み
    assert get_round_level_above(15000) == 16000    # 1000円刻み


def test_get_previous_swing_high_returns_latest_peak():
    values = [1, 2, 3, 3200, 9, 8, 7, 6, 5, 4, 3]
    df = _high_df(values)

    assert get_previous_swing_high(df) == 3200


def test_get_previous_swing_high_returns_none_when_no_peak():
    values = [1, 2, 3, 4, 5]
    df = _high_df(values)

    assert get_previous_swing_high(df) is None


def test_get_previous_swing_low_returns_latest_trough():
    values = [100, 90, 80, 50, 60, 70, 80, 90, 100, 110, 120]
    df = _low_df(values, sma20_last=70)

    assert get_previous_swing_low(df) == 50


def test_take_profit_uses_farther_of_swing_high_and_round_level():
    values = [1, 2, 3, 3200, 9, 8, 7, 6, 5, 4, 3]
    df = _high_df(values)

    # 前回高値3200 < 節目3500 -> 遠い方の3500を採用
    result = get_take_profit_price(df, entry_price=3000, direction="long")

    assert result == 3500


def test_short_take_profit_uses_farther_of_swing_low_and_round_level():
    values = [3000, 2900, 2800, 2650, 2700, 2750, 2800, 2900, 3000, 3100, 3200]
    df = _low_df(values, sma20_last=2900)

    # 前回安値2650、節目2500 -> 遠い方の2500を採用
    result = get_take_profit_price(df, entry_price=3000, direction="short")

    assert result == 2500


def test_take_profit_falls_back_to_round_level_when_swing_high_is_stale():
    values = [1, 2, 3, 3200, 9, 8, 7, 6, 5, 4, 3]
    df = _high_df(values)

    # entry_price(3300) > 前回高値(3200) なので前回高値は候補から除外され、節目3500を採用
    result = get_take_profit_price(df, entry_price=3300, direction="long")

    assert result == 3500


def test_stop_loss_uses_closer_of_swing_low_and_sma20():
    values = [100, 90, 80, 50, 60, 70, 80, 90, 100, 110, 120]
    df = _low_df(values, sma20_last=70)

    # 前回底値50 < 20日線70 -> エントリー価格に近い70(20日線)を採用
    result = get_stop_loss_price(df, entry_price=100, direction="long")

    assert result == 70


def test_stop_loss_falls_back_to_swing_low_when_sma20_is_above_entry():
    values = [100, 90, 80, 50, 60, 70, 80, 90, 100, 110, 120]
    df = _low_df(values, sma20_last=150)

    # 20日線(150)がエントリー価格(100)より上にあるため候補から除外され、前回底値50を採用
    result = get_stop_loss_price(df, entry_price=100, direction="long")

    assert result == 50


def test_calculate_risk_reward_ratio_for_two_to_one():
    ratio = calculate_risk_reward_ratio(
        entry_price=100, stop_loss_price=70, take_profit_price=160, direction="long"
    )

    assert ratio == 2.0


def test_calculate_risk_reward_ratio_is_none_when_stop_loss_missing():
    ratio = calculate_risk_reward_ratio(
        entry_price=100, stop_loss_price=None, take_profit_price=160, direction="long"
    )

    assert ratio is None
