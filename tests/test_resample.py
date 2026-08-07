import pandas as pd

from indicators.resample import resample_to_weekly, resample_to_monthly


def _flat_series(start_date, periods):
    values = list(range(1, periods + 1))

    return pd.DataFrame({
        "code": ["7203"] * periods,
        "date": pd.date_range(start_date, periods=periods, freq="D"),
        "open": values,
        "high": values,
        "low": values,
        "close": values,
        "volume": values,
    })


def test_resample_to_weekly_aggregates_two_full_weeks():
    # 2026-01-05(月) 〜 2026-01-18(日) の2週間分
    df = _flat_series("2026-01-05", 14)

    result = resample_to_weekly(df)

    assert len(result) == 2

    week1 = result.iloc[0]
    assert week1["open"] == 1
    assert week1["high"] == 7
    assert week1["low"] == 1
    assert week1["close"] == 7
    assert week1["volume"] == sum(range(1, 8))

    week2 = result.iloc[1]
    assert week2["open"] == 8
    assert week2["high"] == 14
    assert week2["low"] == 8
    assert week2["close"] == 14
    assert week2["volume"] == sum(range(8, 15))


def test_resample_to_monthly_aggregates_two_full_months():
    # 2026-01-01 〜 2026-02-28 の2ヶ月分
    df = _flat_series("2026-01-01", 59)

    result = resample_to_monthly(df)

    assert len(result) == 2

    january = result.iloc[0]
    assert january["open"] == 1
    assert january["high"] == 31
    assert january["low"] == 1
    assert january["close"] == 31
    assert january["volume"] == sum(range(1, 32))

    february = result.iloc[1]
    assert february["open"] == 32
    assert february["high"] == 59
    assert february["low"] == 32
    assert february["close"] == 59
    assert february["volume"] == sum(range(32, 60))


def test_resample_preserves_code_column():
    df = _flat_series("2026-01-05", 14)

    result = resample_to_weekly(df)

    assert (result["code"] == "7203").all()
