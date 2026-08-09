import pandas as pd

from ui.chart import compute_visible_window


def _df():
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01", "2026-01-02", "2026-01-03",
            "2026-02-01", "2026-02-02",
        ]),
        "high": [110, 120, 115, 200, 205],
        "low": [100, 105, 108, 190, 195],
        "volume": [1000, 1500, 1200, 5000, 4800],
    })


def test_compute_visible_window_filters_to_date_range():
    df = _df()

    x_range, y_range, volume_range = compute_visible_window(
        df, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03")
    )

    assert x_range == [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03")]

    # 対象期間内の安値最小100・高値最大120から余白付きで計算される
    assert y_range[0] < 100
    assert y_range[1] > 120

    assert volume_range[0] == 0
    assert volume_range[1] > 1500


def test_compute_visible_window_excludes_data_outside_range():
    df = _df()

    _, y_range, _ = compute_visible_window(
        df, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03")
    )

    # 2月のデータ（高値200前後）は範囲に含まれないはず
    assert y_range[1] < 150


def test_compute_visible_window_returns_none_ranges_when_no_data_in_window():
    df = _df()

    x_range, y_range, volume_range = compute_visible_window(
        df, pd.Timestamp("2030-01-01"), pd.Timestamp("2030-01-31")
    )

    assert x_range == [pd.Timestamp("2030-01-01"), pd.Timestamp("2030-01-31")]
    assert y_range is None
    assert volume_range is None
