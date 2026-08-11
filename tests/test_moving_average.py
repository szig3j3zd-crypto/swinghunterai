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


def test_sma3_matches_manual_average():
    df = _price_series(4)

    result = calculate_moving_average(df)

    # close = [1, 2, 3, 4] -> 直近3件の平均
    assert result["sma3"].iloc[-1] == (2 + 3 + 4) / 3


def test_sma7_matches_manual_average():
    df = _price_series(8)

    result = calculate_moving_average(df)

    # close = [1..8] -> 直近7件の平均
    assert result["sma7"].iloc[-1] == sum(range(2, 9)) / 7


def test_sma10_matches_manual_average():
    df = _price_series(11)

    result = calculate_moving_average(df)

    # close = [1..11] -> 直近10件の平均
    assert result["sma10"].iloc[-1] == sum(range(2, 12)) / 10


def test_sma20_matches_manual_average():
    df = _price_series(20)

    result = calculate_moving_average(df)

    # close = [1..20] -> 直近20件の平均
    assert result["sma20"].iloc[-1] == sum(range(1, 21)) / 20


def test_sma60_is_nan_when_not_enough_history():
    df = _price_series(10)

    result = calculate_moving_average(df)

    assert result["sma60"].isna().all()


def test_sma300_is_nan_when_not_enough_history():
    df = _price_series(10)

    result = calculate_moving_average(df)

    assert result["sma300"].isna().all()
