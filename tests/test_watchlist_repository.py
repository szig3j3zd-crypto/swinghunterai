from database.watchlist_repository import (
    add_watchlist_stock,
    create_table,
    delete_watchlist_stock,
    delete_watchlist_stocks_by_code,
    get_all_watchlist_stocks,
    update_watchlist_priority,
    update_watchlist_timeframe,
    watchlist_stock_exists,
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
        assert added["priority"] == 0

        update_watchlist_timeframe(added["id"], "weekly")

        updated = next(s for s in get_all_watchlist_stocks() if s["id"] == added["id"])
        assert updated["timeframe"] == "weekly"

        update_watchlist_priority(added["id"], True)
        prioritized = next(
            s for s in get_all_watchlist_stocks() if s["id"] == added["id"]
        )
        assert prioritized["priority"] == 1

        update_watchlist_priority(added["id"], False)
        unprioritized = next(
            s for s in get_all_watchlist_stocks() if s["id"] == added["id"]
        )
        assert unprioritized["priority"] == 0

    finally:
        delete_watchlist_stock(added["id"])

    assert not any(s["id"] == added["id"] for s in get_all_watchlist_stocks())


def test_add_watchlist_stock_with_priority_true_registers_as_priority():
    create_table()

    add_watchlist_stock(
        code="9995",
        company_name="テスト銘柄5",
        direction="long",
        timeframe="daily",
        added_date="2000-01-01",
        priority=True,
    )

    added = next(s for s in get_all_watchlist_stocks() if s["code"] == "9995")

    try:
        assert added["priority"] == 1
    finally:
        delete_watchlist_stock(added["id"])


def test_add_watchlist_stock_skips_duplicate_code_direction_timeframe():
    create_table()

    added = add_watchlist_stock(
        code="9998",
        company_name="テスト銘柄3",
        direction="long",
        timeframe="daily",
        added_date="2000-01-01",
    )
    duplicate_added = add_watchlist_stock(
        code="9998",
        company_name="テスト銘柄3",
        direction="long",
        timeframe="daily",
        added_date="2000-01-02",
    )

    try:
        assert added is True
        assert duplicate_added is False
        assert sum(1 for s in get_all_watchlist_stocks() if s["code"] == "9998") == 1
        assert watchlist_stock_exists("9998", "long", "daily") is True
        assert watchlist_stock_exists("9998", "short", "daily") is False

    finally:
        delete_watchlist_stocks_by_code("9998")


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
