import pandas as pd

from config.config import LARGE_CAP_MARKET_CAP_THRESHOLD
from database.stock_master_reader import get_active_stocks
from database.trade_repository import (
    add_trade,
    create_table as create_trades_table,
    delete_trade,
    get_all_trades,
)
from database.watchlist_repository import (
    add_watchlist_stock,
    create_table as create_watchlist_table,
    delete_watchlist_stocks_by_code,
)
from service.screening_service import (
    evaluate_single_stock,
    format_reason,
    get_large_cap_stocks,
    get_prime_stocks,
    get_stock_chart_data,
    get_today_candidates,
    get_today_scan_results,
    get_today_watchlist,
)


def test_get_large_cap_stocks_returns_stocks_above_threshold_only():
    stocks = get_large_cap_stocks()

    assert len(stocks) > 0
    assert (stocks["market_cap"] >= LARGE_CAP_MARKET_CAP_THRESHOLD).all()


def test_get_prime_stocks_returns_prime_market_only():
    stocks = get_prime_stocks()

    assert len(stocks) > 0
    assert set(stocks["market"].unique()) == {"プライム（内国株式）"}


def test_get_today_candidates_runs_on_a_small_universe():
    stocks = get_active_stocks().head(3)

    # min_market_cap=0: 時価総額フィルタ（config既定で有効）を無効化し、
    # テストがYahoo Financeへライブ通信するのを防ぐ
    candidates = get_today_candidates(direction="long", stocks=stocks, min_market_cap=0)

    assert isinstance(candidates, list)

    for candidate in candidates:
        assert candidate["is_entry_candidate"] is True
        assert "code" in candidate
        assert "company_name" in candidate


def test_candidates_are_sorted_by_score_descending():
    stocks = get_active_stocks().head(10)

    candidates = get_today_candidates(direction="long", stocks=stocks, min_market_cap=0)

    scores = [c["score"]["total_score"] for c in candidates]

    assert scores == sorted(scores, reverse=True)


def test_get_today_watchlist_runs_on_a_small_universe():
    stocks = get_active_stocks().head(3)

    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["ma_order", "bounce"],
    )

    assert isinstance(watchlist, list)

    for watch_item in watchlist:
        assert watch_item["is_watch_candidate"] is True
        assert watch_item["is_entry_candidate"] is False
        assert "code" in watch_item
        assert "company_name" in watch_item


def test_get_today_watchlist_is_always_empty_without_bounce_module():
    stocks = get_active_stocks().head(3)

    watchlist = get_today_watchlist(direction="long", stocks=stocks, modules=["ma_order"])

    assert watchlist == []


def test_get_today_scan_results_excludes_open_trade_codes():
    create_trades_table()

    stocks = get_active_stocks().head(5)
    code = stocks.iloc[0]["code"]
    company_name = stocks.iloc[0]["company_name"]

    add_trade(
        code=code, company_name=company_name, direction="long", timeframe="daily",
        trade_date="2000-01-01", entry_price=100.0, exit_price=None, quantity=100,
    )

    try:
        result = get_today_scan_results(
            direction="long", stocks=stocks, modules=[],
            min_volume=0, min_price=0, max_price=float("inf"), min_market_cap=0,
        )

        assert code not in [c["code"] for c in result["candidates"]]
    finally:
        for trade in get_all_trades():
            if trade["code"] == code and trade["trade_date"] == "2000-01-01":
                delete_trade(trade["id"])


def test_get_today_scan_results_does_not_exclude_closed_trade_codes():
    create_trades_table()

    stocks = get_active_stocks().head(5)
    code = stocks.iloc[0]["code"]
    company_name = stocks.iloc[0]["company_name"]

    add_trade(
        code=code, company_name=company_name, direction="long", timeframe="daily",
        trade_date="2000-01-01", entry_price=100.0, exit_price=110.0, quantity=100,
    )

    try:
        result = get_today_scan_results(
            direction="long", stocks=stocks, modules=[],
            min_volume=0, min_price=0, max_price=float("inf"), min_market_cap=0,
        )

        assert code in [c["code"] for c in result["candidates"]]
    finally:
        for trade in get_all_trades():
            if trade["code"] == code and trade["trade_date"] == "2000-01-01":
                delete_trade(trade["id"])


def test_get_today_scan_results_excludes_watchlist_codes():
    create_watchlist_table()

    stocks = get_active_stocks().head(5)
    code = stocks.iloc[0]["code"]
    company_name = stocks.iloc[0]["company_name"]

    add_watchlist_stock(
        code=code, company_name=company_name, direction="long", timeframe="daily",
        added_date="2000-01-01",
    )

    try:
        result = get_today_scan_results(
            direction="long", stocks=stocks, modules=[],
            min_volume=0, min_price=0, max_price=float("inf"), min_market_cap=0,
        )

        assert code not in [c["code"] for c in result["candidates"]]
    finally:
        delete_watchlist_stocks_by_code(code)


def test_get_today_scan_results_with_empty_modules_skips_judgment():
    stocks = get_active_stocks().head(5)

    # min_market_cap=0: 時価総額フィルタ（config既定で有効）を無効化し、
    # テストがYahoo Financeへライブ通信するのを防ぐ
    result = get_today_scan_results(
        direction="long", stocks=stocks, modules=[],
        min_volume=0, min_price=0, max_price=float("inf"), min_market_cap=0,
    )

    assert result["watchlist"] == []

    for candidate in result["candidates"]:
        assert candidate.get("no_modules_selected") is True
        assert "code" in candidate
        assert "company_name" in candidate
        assert "price" in candidate
        assert "score" not in candidate

    assert [c["code"] for c in result["candidates"]] == sorted(
        c["code"] for c in result["candidates"]
    )


def test_get_today_scan_results_with_empty_modules_applies_price_filter():
    stocks = get_active_stocks().head(5)

    result = get_today_scan_results(
        direction="long", stocks=stocks, modules=[],
        min_volume=0, min_price=0, max_price=0,
    )

    assert result["candidates"] == []


def test_get_today_scan_results_matches_separate_calls():
    stocks = get_active_stocks().head(10)

    result = get_today_scan_results(
        direction="long", stocks=stocks, modules=["ma_order", "bounce"], min_market_cap=0,
    )

    assert set(result.keys()) == {"candidates", "watchlist"}

    expected_candidates = get_today_candidates(
        direction="long", stocks=stocks, modules=["ma_order", "bounce"], min_market_cap=0,
    )
    expected_watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["ma_order", "bounce"],
    )

    assert [c["code"] for c in result["candidates"]] == [c["code"] for c in expected_candidates]
    assert (
        sorted(w["code"] for w in result["watchlist"])
        == sorted(w["code"] for w in expected_watchlist)
    )
    assert all(c["is_entry_candidate"] for c in result["candidates"])
    assert all(w["is_watch_candidate"] for w in result["watchlist"])


def test_evaluate_single_stock_returns_error_for_unknown_code():
    result = evaluate_single_stock("0000")

    assert result["code"] == "0000"
    assert "error" in result


def test_evaluate_single_stock_with_empty_modules_skips_judgment():
    code = get_active_stocks().iloc[0]["code"]

    result = evaluate_single_stock(code, direction="long", modules=[])

    assert result["code"] == code
    assert "company_name" in result
    assert result.get("no_modules_selected") is True
    assert result["direction"] == "long"
    assert "is_entry_candidate" not in result
    assert "price" in result


def test_evaluate_single_stock_returns_result_for_known_code():
    code = get_active_stocks().iloc[0]["code"]

    result = evaluate_single_stock(code, direction="long")

    assert result["code"] == code
    assert "company_name" in result
    # データ不足なら error、十分なら is_entry_candidate（True/False問わず）を持つ
    assert "error" in result or "is_entry_candidate" in result


def test_get_stock_chart_data_returns_ohlcv_and_moving_averages():
    code = get_active_stocks().iloc[0]["code"]

    df = get_stock_chart_data(code, timeframe="daily")

    for column in ["date", "open", "high", "low", "close", "volume",
                   "sma5", "sma20", "sma60", "sma100"]:
        assert column in df.columns

    assert list(df["date"]) == sorted(df["date"])


def test_get_stock_chart_data_weekly_has_fewer_rows_than_daily():
    code = get_active_stocks().iloc[0]["code"]

    daily = get_stock_chart_data(code, timeframe="daily")
    weekly = get_stock_chart_data(code, timeframe="weekly")

    assert len(weekly) < len(daily)


def test_get_stock_chart_data_monthly_has_fewer_rows_than_weekly():
    code = get_active_stocks().iloc[0]["code"]

    weekly = get_stock_chart_data(code, timeframe="weekly")
    monthly = get_stock_chart_data(code, timeframe="monthly")

    assert len(monthly) < len(weekly)


def test_format_reason_joins_module_labels():
    candidate = {"modules": ["ma_order", "perfect_golden_cross"], "bounce_number": None}

    assert format_reason(candidate) == "並び順＋完全ゴールデンクロス"


def test_format_reason_appends_bounce_number():
    candidate = {"modules": ["bounce"], "bounce_number": 2}

    assert format_reason(candidate) == "反発（反発2回目）"


def test_format_reason_uses_short_labels_for_short_direction():
    candidate = {
        "modules": ["ma_order", "perfect_golden_cross", "parallel_rise"],
        "bounce_number": None,
        "direction": "short",
    }

    assert format_reason(candidate) == "並び順＋完全デッドクロス＋並走下降"


def test_format_reason_uses_dead_cross_label_for_short_golden_cross_module():
    candidate = {"modules": ["golden_cross"], "bounce_number": None, "direction": "short"}

    assert format_reason(candidate) == "デッドクロス"
