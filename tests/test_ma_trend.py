import pandas as pd

from analysis.ma_trend import (
    get_current_trend_period,
    get_ma_order,
    get_ma_slope,
    is_long_trend,
    is_short_trend,
)


def _df(sma5, sma20, sma60):
    return pd.DataFrame({
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
    })


def test_ma_order_long_when_5_above_20_above_60():
    df = _df([15], [12], [10])

    assert get_ma_order(df) == "long"


def test_ma_order_short_when_60_above_20_above_5():
    df = _df([10], [12], [15])

    assert get_ma_order(df) == "short"


def test_ma_order_mixed_otherwise():
    df = _df([12], [15], [10])

    assert get_ma_order(df) == "mixed"


def test_ma_slope_up_when_current_greater_than_previous():
    series = pd.Series([10, 11])

    assert get_ma_slope(series, lookback=1) == "up"


def test_ma_slope_down_when_current_less_than_previous():
    series = pd.Series([11, 10])

    assert get_ma_slope(series, lookback=1) == "down"


def test_ma_slope_flat_when_unchanged():
    series = pd.Series([10, 10])

    assert get_ma_slope(series, lookback=1) == "flat"


def test_is_long_trend_true_when_order_and_all_slopes_are_up():
    df = _df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma60=[5, 10],
    )

    assert is_long_trend(df) is True


def test_is_long_trend_false_when_order_correct_but_one_slope_is_down():
    df = _df(
        sma5=[10, 15],
        sma20=[12, 12],  # 横ばい
        sma60=[5, 10],
    )

    assert is_long_trend(df) is False


def test_is_short_trend_true_when_order_and_all_slopes_are_down():
    df = _df(
        sma5=[15, 10],
        sma20=[20, 15],
        sma60=[30, 25],
    )

    assert is_short_trend(df) is True


def _trend_df():
    df = _df(
        sma5=[1, 2, 10, 11, 12, 13],
        sma20=[1, 2, 9, 10, 11, 12],
        sma60=[1, 2, 8, 9, 10, 11],
    )
    df["date"] = pd.date_range("2026-01-01", periods=6, freq="D")
    return df


def test_get_current_trend_period_returns_start_of_ongoing_trend():
    df = _trend_df()

    start_date = get_current_trend_period(df, direction="long")

    # day2(2026-01-03)からロングトレンドが始まり、直近日まで継続している
    assert start_date == pd.Timestamp("2026-01-03")


def test_get_current_trend_period_returns_none_when_not_trending():
    df = _trend_df()
    df.loc[df.index[-1], "sma5"] = 1  # 直近日で並び順が崩れる

    start_date = get_current_trend_period(df, direction="long")

    assert start_date is None
