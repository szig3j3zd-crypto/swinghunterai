import pandas as pd

from data.validator.data_validator import DataValidator


def _valid_data():
    return pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "Open": [100.0, 101.0, 102.0],
        "High": [101.0, 102.0, 103.0],
        "Low": [99.0, 100.0, 101.0],
        "Close": [100.5, 101.5, 102.5],
        "Volume": [1000, 1100, 1200],
    })


def test_valid_data_passes():
    assert DataValidator.validate(_valid_data()) is True


def test_none_fails():
    assert DataValidator.validate(None) is False


def test_missing_column_fails():
    data = _valid_data().drop(columns=["Volume"])

    assert DataValidator.validate(data) is False


def test_null_value_fails():
    data = _valid_data()
    data.loc[0, "Close"] = None

    assert DataValidator.validate(data) is False


def test_duplicate_date_fails():
    data = _valid_data()
    data.loc[1, "Date"] = data.loc[0, "Date"]

    assert DataValidator.validate(data) is False


def test_unsorted_date_fails():
    data = _valid_data().iloc[::-1].reset_index(drop=True)

    assert DataValidator.validate(data) is False
