from database.stock_master_repository import get_all
from database.stock_master_reader import get_active_stocks


VALID_MARKETS = {
    "プライム（内国株式）",
    "スタンダード（内国株式）",
    "グロース（内国株式）",
}


def test_get_all_returns_stocks():
    stocks = get_all()

    assert len(stocks) > 0


def test_active_stocks_are_limited_to_target_markets():
    stocks = get_active_stocks()

    assert len(stocks) > 0
    assert set(stocks["market"].unique()).issubset(VALID_MARKETS)
