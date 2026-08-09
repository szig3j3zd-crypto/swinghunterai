from service.trade_service import calculate_pnl, group_by_year_and_month, total_pnl


def _trade(direction, entry_price, exit_price, quantity, trade_date="2026-08-01"):
    return {
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": quantity,
        "trade_date": trade_date,
    }


def test_calculate_pnl_long_profit():
    trade = _trade("long", entry_price=1000, exit_price=1200, quantity=100)

    assert calculate_pnl(trade) == 20_000


def test_calculate_pnl_long_loss():
    trade = _trade("long", entry_price=1000, exit_price=900, quantity=100)

    assert calculate_pnl(trade) == -10_000


def test_calculate_pnl_short_profit():
    trade = _trade("short", entry_price=1000, exit_price=800, quantity=100)

    assert calculate_pnl(trade) == 20_000


def test_calculate_pnl_short_loss():
    trade = _trade("short", entry_price=1000, exit_price=1100, quantity=100)

    assert calculate_pnl(trade) == -10_000


def test_calculate_pnl_none_when_not_closed():
    trade = _trade("long", entry_price=1000, exit_price=None, quantity=100)

    assert calculate_pnl(trade) is None


def test_total_pnl_excludes_open_trades():
    trades = [
        _trade("long", 1000, 1200, 100),   # +20,000
        _trade("long", 1000, 900, 100),    # -10,000
        _trade("long", 1000, None, 100),   # 未決済（除外）
    ]

    assert total_pnl(trades) == 10_000


def test_group_by_year_and_month_orders_descending_and_sums_pnl():
    trades = [
        _trade("long", 1000, 1100, 100, trade_date="2025-03-10"),  # +10,000
        _trade("long", 1000, 900, 100, trade_date="2025-03-20"),   # -10,000
        _trade("long", 1000, 1200, 100, trade_date="2026-01-05"),  # +20,000
    ]

    groups = group_by_year_and_month(trades)

    assert [year for year, _, _ in groups] == [2026, 2025]

    year_2026, pnl_2026, months_2026 = groups[0]
    assert pnl_2026 == 20_000
    assert [month for month, _, _ in months_2026] == [1]

    year_2025, pnl_2025, months_2025 = groups[1]
    assert pnl_2025 == 0
    assert [month for month, _, _ in months_2025] == [3]
    assert len(months_2025[0][2]) == 2
