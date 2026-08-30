from config.config import CAPITAL_GAINS_TAX_RATE
from service.trade_service import calculate_pnl, group_by_year_and_month, total_pnl


def _after_tax(net_gross_pnl):
    if net_gross_pnl <= 0:
        return net_gross_pnl
    return net_gross_pnl * (1 - CAPITAL_GAINS_TAX_RATE)


def _trade(direction, entry_price, exit_price, quantity, trade_date="2026-08-01",
           is_nisa=False):
    return {
        "direction": direction,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": quantity,
        "trade_date": trade_date,
        "is_nisa": is_nisa,
    }


def test_calculate_pnl_long_profit_is_gross():
    trade = _trade("long", entry_price=1000, exit_price=1200, quantity=100)

    assert calculate_pnl(trade) == 20_000


def test_calculate_pnl_long_loss_is_gross():
    trade = _trade("long", entry_price=1000, exit_price=900, quantity=100)

    assert calculate_pnl(trade) == -10_000


def test_calculate_pnl_short_profit_is_gross():
    trade = _trade("short", entry_price=1000, exit_price=800, quantity=100)

    assert calculate_pnl(trade) == 20_000


def test_calculate_pnl_short_loss_is_gross():
    trade = _trade("short", entry_price=1000, exit_price=1100, quantity=100)

    assert calculate_pnl(trade) == -10_000


def test_calculate_pnl_none_when_not_closed():
    trade = _trade("long", entry_price=1000, exit_price=None, quantity=100)

    assert calculate_pnl(trade) is None


def test_total_pnl_nets_gains_and_losses_before_taxing():
    trades = [
        _trade("long", 1000, 1200, 100),   # +20,000（税引前）
        _trade("long", 1000, 900, 100),    # -10,000
        _trade("long", 1000, None, 100),   # 未決済（除外）
    ]

    # 個別課税ではなく、+20,000と-10,000を通算した+10,000に対して課税する
    assert total_pnl(trades) == _after_tax(10_000)


def test_total_pnl_no_tax_when_net_is_a_loss():
    trades = [
        _trade("long", 1000, 1100, 100),  # +10,000（税引前）
        _trade("long", 1000, 800, 100),   # -20,000
    ]

    assert total_pnl(trades) == -10_000


def test_total_pnl_excludes_nisa_from_taxable_netting():
    trades = [
        _trade("long", 1000, 1200, 100),                    # +20,000（特定口座、課税対象）
        _trade("long", 1000, 900, 100),                      # -10,000（特定口座、課税対象）
        _trade("long", 1000, 1500, 100, is_nisa=True),       # +50,000（NISA、常に非課税）
    ]

    # 特定口座分は+20,000と-10,000を通算した+10,000に課税、NISA分はそのまま加算
    assert total_pnl(trades) == _after_tax(10_000) + 50_000


def test_group_by_year_and_month_orders_descending_nets_tax_per_year():
    trades = [
        _trade("long", 1000, 1100, 100, trade_date="2025-03-10"),  # +10,000
        _trade("long", 1000, 900, 100, trade_date="2025-03-20"),   # -10,000
        _trade("long", 1000, 1200, 100, trade_date="2026-01-05"),  # +20,000
    ]

    groups = group_by_year_and_month(trades)

    assert [year for year, _, _ in groups] == [2026, 2025]

    year_2026, pnl_2026, months_2026 = groups[0]
    assert pnl_2026 == _after_tax(20_000)
    assert [month for month, _, _ in months_2026] == [1]
    # 月間損益は税引前（グロス）の単純合計
    assert months_2026[0][1] == 20_000

    year_2025, pnl_2025, months_2025 = groups[1]
    # 2025年内で+10,000と-10,000を通算するとゼロなので非課税
    assert pnl_2025 == 0
    assert [month for month, _, _ in months_2025] == [3]
    assert months_2025[0][1] == 0
    assert len(months_2025[0][2]) == 2
