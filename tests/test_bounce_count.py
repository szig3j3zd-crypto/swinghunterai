import pandas as pd

from rules.bounce_count import get_bounce_number, is_entry_candidate


def _df(length):
    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
    })


def test_close_events_are_merged_into_one_bounce():
    df = _df(20)
    signal = pd.Series(False, index=df.index)
    signal.iloc[2] = True
    signal.iloc[4] = True  # day2との差は2行 -> 同一グループ
    signal.iloc[15] = True  # day4との差は11行 -> 別グループ

    result = get_bounce_number(
        df, signal, start_date=df["date"].iloc[0], merge_within_days=5
    )

    assert result.iloc[2] == 1
    assert result.iloc[4] == 1
    assert result.iloc[15] == 2
    assert result.isna().sum() == 17


def test_events_before_start_date_are_ignored():
    df = _df(20)
    signal = pd.Series(False, index=df.index)
    signal.iloc[2] = True
    signal.iloc[15] = True

    result = get_bounce_number(
        df, signal, start_date=df["date"].iloc[3], merge_within_days=5
    )

    assert pd.isna(result.iloc[2])
    assert result.iloc[15] == 1


def test_no_signal_returns_all_nan():
    df = _df(10)
    signal = pd.Series(False, index=df.index)

    result = get_bounce_number(df, signal, start_date=df["date"].iloc[0])

    assert result.isna().all()


def test_is_entry_candidate_excludes_third_bounce_onward():
    df = _df(30)
    signal = pd.Series(False, index=df.index)
    signal.iloc[0] = True
    signal.iloc[10] = True
    signal.iloc[20] = True

    bounce_number = get_bounce_number(
        df, signal, start_date=df["date"].iloc[0], merge_within_days=5
    )
    result = is_entry_candidate(bounce_number, max_bounces=2)

    assert bool(result.iloc[0]) is True
    assert bool(result.iloc[10]) is True
    assert bool(result.iloc[20]) is False
