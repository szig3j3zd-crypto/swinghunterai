import pandas as pd

from analysis.price_zones import cluster_price_points


def test_close_prices_are_merged_into_one_zone():
    points = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01", "2026-02-01", "2026-03-01",
        ]),
        "price": [99, 100, 101],
    })

    zones = cluster_price_points(points, threshold=0.02)

    assert len(zones) == 1
    assert zones[0]["touch_count"] == 3
    assert zones[0]["price"] == (99 + 100 + 101) / 3
    assert zones[0]["first_touch_date"] == pd.Timestamp("2026-01-01")
    assert zones[0]["last_touch_date"] == pd.Timestamp("2026-03-01")


def test_far_apart_prices_form_separate_zones():
    points = pd.DataFrame({
        "date": pd.to_datetime([
            "2026-01-01", "2026-02-01",
        ]),
        "price": [100, 150],
    })

    zones = cluster_price_points(points, threshold=0.02)

    assert len(zones) == 2
    assert zones[0]["price"] == 100
    assert zones[0]["touch_count"] == 1
    assert zones[1]["price"] == 150
    assert zones[1]["touch_count"] == 1
