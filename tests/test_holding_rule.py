import pandas as pd

from rules.holding_rule import evaluate_holding, get_holding_days


def _df(length):
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
    })


def test_get_holding_days_counts_rows_since_entry():
    df = _df(21)
    entry_date = df["date"].iloc[5]

    result = get_holding_days(df, entry_date)

    assert result == 15  # 直近行(20) - エントリー行(5)


def test_get_holding_days_returns_none_when_entry_date_not_found():
    df = _df(10)

    result = get_holding_days(df, entry_date=pd.Timestamp("2099-01-01"))

    assert result is None


def test_needs_review_false_when_within_threshold():
    df = _df(15)
    entry_date = df["date"].iloc[0]  # 経過14営業日

    result = evaluate_holding(df, entry_date, max_holding_days=20)

    assert result["holding_days"] == 14
    assert result["needs_review"] is False


def test_needs_review_true_when_threshold_exceeded():
    df = _df(25)
    entry_date = df["date"].iloc[0]  # 経過24営業日

    result = evaluate_holding(df, entry_date, max_holding_days=20)

    assert result["holding_days"] == 24
    assert result["needs_review"] is True


def test_needs_review_true_exactly_at_threshold():
    df = _df(21)
    entry_date = df["date"].iloc[0]  # 経過20営業日 = しきい値ぴったり

    result = evaluate_holding(df, entry_date, max_holding_days=20)

    assert result["needs_review"] is True


def test_falls_back_to_config_default_when_not_specified():
    df = _df(10)
    entry_date = df["date"].iloc[0]

    result = evaluate_holding(df, entry_date)

    assert result["holding_days"] == 9
    assert result["needs_review"] is False
