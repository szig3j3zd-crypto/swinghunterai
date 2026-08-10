from database.watchlist_repository import (
    add_watchlist_stock,
    create_table,
    delete_watchlist_stock,
    get_all_watchlist_stocks,
    update_watchlist_timeframe,
)


def test_add_delete_watchlist_stock_roundtrip():
    create_table()

    add_watchlist_stock(
        code="9999",
        company_name="テスト銘柄",
        direction="long",
        timeframe="daily",
        added_date="2000-01-01",
    )

    added = next(
        s for s in get_all_watchlist_stocks()
        if s["code"] == "9999" and s["added_date"] == "2000-01-01"
    )

    try:
        assert added["company_name"] == "テスト銘柄"
        assert added["direction"] == "long"
        assert added["timeframe"] == "daily"

        update_watchlist_timeframe(added["id"], "weekly")

        updated = next(s for s in get_all_watchlist_stocks() if s["id"] == added["id"])
        assert updated["timeframe"] == "weekly"

    finally:
        delete_watchlist_stock(added["id"])

    assert not any(s["id"] == added["id"] for s in get_all_watchlist_stocks())
