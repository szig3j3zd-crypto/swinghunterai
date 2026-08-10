from database.watchlist_repository import (
    add_watchlist_stock,
    create_table,
    delete_watchlist_stock,
    delete_watchlist_stocks_by_code,
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


def test_delete_watchlist_stocks_by_code_removes_all_matching_entries():
    create_table()

    add_watchlist_stock(
        code="9996",
        company_name="テスト銘柄4",
        direction="long",
        timeframe="daily",
        added_date="2000-01-01",
    )
    add_watchlist_stock(
        code="9996",
        company_name="テスト銘柄4",
        direction="long",
        timeframe="weekly",
        added_date="2000-01-02",
    )

    deleted_count = delete_watchlist_stocks_by_code("9996")

    assert deleted_count == 2
    assert not any(s["code"] == "9996" for s in get_all_watchlist_stocks())
