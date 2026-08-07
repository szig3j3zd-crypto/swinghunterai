import pandas as pd

from indicators.volume import calculate_volume_indicators


def _volume_series(length):
    return pd.DataFrame({
        "code": ["7203"] * length,
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "volume": list(range(100, 100 + length)),
    })


def test_volume_avg_matches_manual_average():
    df = _volume_series(20)

    result = calculate_volume_indicators(df)

    # volume = [100..119] -> 直近20件の平均
    assert result["volume_avg"].iloc[-1] == sum(range(100, 120)) / 20


def test_volume_ratio_matches_manual_calculation():
    df = _volume_series(20)

    result = calculate_volume_indicators(df)

    expected_ratio = (
        result["volume"].iloc[-1] / result["volume_avg"].iloc[-1]
    )

    assert result["volume_ratio"].iloc[-1] == expected_ratio


def test_volume_avg_is_nan_when_not_enough_history():
    df = _volume_series(10)

    result = calculate_volume_indicators(df)

    assert result["volume_avg"].isna().all()


def test_row_count_is_unchanged():
    df = _volume_series(10)

    result = calculate_volume_indicators(df)

    assert len(result) == len(df)
