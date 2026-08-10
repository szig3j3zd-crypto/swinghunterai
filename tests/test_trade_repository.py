from database.trade_repository import (
    add_trade,
    create_table,
    delete_trade,
    get_all_trades,
    has_open_trade,
    update_trade,
)


def test_add_update_delete_trade_roundtrip():
    create_table()

    add_trade(
        code="9999",
        company_name="テスト銘柄",
        direction="long",
        timeframe="daily",
        trade_date="2000-01-01",
        entry_price=1000,
        exit_price=None,
        quantity=100,
    )

    added = next(
        t for t in get_all_trades()
        if t["code"] == "9999" and t["trade_date"] == "2000-01-01"
    )

    try:
        assert added["direction"] == "long"
        assert added["timeframe"] == "daily"
        assert added["entry_price"] == 1000
        assert added["exit_price"] is None
        assert added["quantity"] == 100

        update_trade(
            added["id"],
            entry_price=1050,
            exit_price=1200,
            quantity=200,
            timeframe="weekly",
        )

        updated = next(t for t in get_all_trades() if t["id"] == added["id"])

        assert updated["entry_price"] == 1050
        assert updated["exit_price"] == 1200
        assert updated["quantity"] == 200
        assert updated["timeframe"] == "weekly"

    finally:
        delete_trade(added["id"])

    assert not any(t["id"] == added["id"] for t in get_all_trades())


def test_has_open_trade_true_when_exit_price_is_none():
    create_table()

    add_trade(
        code="9998",
        company_name="テスト銘柄2",
        direction="long",
        timeframe="daily",
        trade_date="2000-01-01",
        entry_price=1000,
        exit_price=None,
        quantity=100,
    )

    added = next(
        t for t in get_all_trades()
        if t["code"] == "9998" and t["trade_date"] == "2000-01-01"
    )

    try:
        assert has_open_trade("9998") is True
    finally:
        delete_trade(added["id"])

    assert has_open_trade("9998") is False


def test_has_open_trade_false_when_only_closed_trades():
    create_table()

    add_trade(
        code="9997",
        company_name="テスト銘柄3",
        direction="long",
        timeframe="daily",
        trade_date="2000-01-01",
        entry_price=1000,
        exit_price=1100,
        quantity=100,
    )

    added = next(
        t for t in get_all_trades()
        if t["code"] == "9997" and t["trade_date"] == "2000-01-01"
    )

    try:
        assert has_open_trade("9997") is False
    finally:
        delete_trade(added["id"])
