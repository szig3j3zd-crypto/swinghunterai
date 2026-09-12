from database.practice_trade_repository import (
    add_practice_trade,
    create_table,
    delete_practice_trade,
    get_all_practice_trades,
    update_practice_trade,
)


def test_add_delete_practice_trade_roundtrip():
    create_table()

    add_practice_trade(
        code="9999",
        company_name="テスト銘柄",
        direction="long",
        trade_date="2000-01-01",
        entry_price=1000.0,
        exit_price=None,
        quantity=100,
    )

    added = next(
        t for t in get_all_practice_trades()
        if t["code"] == "9999" and t["trade_date"] == "2000-01-01"
    )

    try:
        assert added["company_name"] == "テスト銘柄"
        assert added["direction"] == "long"
        assert added["entry_price"] == 1000.0
        assert added["exit_price"] is None
        assert added["exit_date"] is None
        assert added["quantity"] == 100

        update_practice_trade(
            added["id"],
            direction="long",
            trade_date="2000-01-02",
            entry_price=1000.0,
            exit_price=1100.0,
            quantity=100,
            exit_date="2000-01-05",
        )

        updated = next(
            t for t in get_all_practice_trades() if t["id"] == added["id"]
        )
        assert updated["trade_date"] == "2000-01-02"
        assert updated["exit_price"] == 1100.0
        assert updated["exit_date"] == "2000-01-05"

    finally:
        delete_practice_trade(added["id"])

    assert not any(t["id"] == added["id"] for t in get_all_practice_trades())


def test_add_practice_trade_stores_exit_date():
    create_table()

    add_practice_trade(
        code="9996",
        company_name="テスト銘柄3",
        direction="long",
        trade_date="2000-01-01",
        entry_price=1000.0,
        exit_price=1200.0,
        quantity=100,
        exit_date="2000-01-10",
    )

    added = next(
        t for t in get_all_practice_trades()
        if t["code"] == "9996" and t["trade_date"] == "2000-01-01"
    )

    try:
        assert added["exit_date"] == "2000-01-10"
    finally:
        delete_practice_trade(added["id"])


def test_get_all_practice_trades_orders_by_trade_date_ascending():
    create_table()

    add_practice_trade(
        code="9997",
        company_name="テスト銘柄2",
        direction="short",
        trade_date="2000-02-01",
        entry_price=500.0,
        exit_price=None,
        quantity=100,
    )
    add_practice_trade(
        code="9997",
        company_name="テスト銘柄2",
        direction="short",
        trade_date="2000-01-01",
        entry_price=500.0,
        exit_price=None,
        quantity=100,
    )

    trades = [t for t in get_all_practice_trades() if t["code"] == "9997"]

    try:
        assert [t["trade_date"] for t in trades] == ["2000-01-01", "2000-02-01"]
    finally:
        for trade in trades:
            delete_practice_trade(trade["id"])
