import pandas as pd

from indicators.moving_average import calculate_moving_average


def _price_series(length):
    return pd.DataFrame({
        "code": ["7203"] * length,
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "close": list(range(1, length + 1)),
    })


def test_sma5_matches_manual_average():
    df = _price_series(6)

    result = calculate_moving_average(df)

    # close = [1, 2, 3, 4, 5, 6] -> 直近5件の平均
    assert result["sma5"].iloc[-1] == (2 + 3 + 4 + 5 + 6) / 5


def test_row_count_is_unchanged():
    df = _price_series(10)

    result = calculate_moving_average(df)

    assert len(result) == len(df)


def test_sma75_is_nan_when_not_enough_history():
    df = _price_series(10)

    result = calculate_moving_average(df)

    assert result["sma75"].isna().all()
