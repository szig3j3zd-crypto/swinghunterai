from database.trade_repository import (
    add_trade,
    delete_trade,
    get_all_trades,
    update_trade,
)


def test_add_update_delete_trade_roundtrip():
    add_trade(
        code="9999",
        company_name="テスト銘柄",
        direction="long",
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
        assert added["entry_price"] == 1000
        assert added["exit_price"] is None
        assert added["quantity"] == 100

        update_trade(added["id"], entry_price=1050, exit_price=1200, quantity=200)

        updated = next(t for t in get_all_trades() if t["id"] == added["id"])

        assert updated["entry_price"] == 1050
        assert updated["exit_price"] == 1200
        assert updated["quantity"] == 200

    finally:
        delete_trade(added["id"])

    assert not any(t["id"] == added["id"] for t in get_all_trades())
