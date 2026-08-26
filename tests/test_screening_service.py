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
    _is_merged_watch_candidate,
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

    # "ma_order"は含めない（ma_order自体も監視銘柄候補を出すようになったため、
    # 含めるとis_watch_candidateがFalseの項目も混ざりうる。ここではbounce単体の
    # 挙動だけを確認したい）
    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["bounce"],
    )

    assert isinstance(watchlist, list)

    for watch_item in watchlist:
        assert watch_item["is_watch_candidate"] is True
        assert watch_item["is_cross_watch_candidate"] is False
        assert watch_item["is_order_watch_candidate"] is False
        assert watch_item["is_entry_candidate"] is False
        assert "code" in watch_item
        assert "company_name" in watch_item


def test_get_today_watchlist_is_always_empty_without_any_watch_module():
    # bounce・ma_cross_watch・ma_orderのいずれも含まない場合は常に空リスト
    # （perfect_golden_crossはエントリー候補判定のみに関与し、監視の役割を持たない）
    stocks = get_active_stocks().head(3)

    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["perfect_golden_cross"],
    )

    assert watchlist == []


def test_get_today_watchlist_runs_with_ma_cross_watch_module():
    stocks = get_active_stocks().head(3)

    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["ma_cross_watch"],
    )

    assert isinstance(watchlist, list)

    for watch_item in watchlist:
        assert watch_item["is_cross_watch_candidate"] is True
        assert watch_item["is_watch_candidate"] is False
        assert watch_item["is_order_watch_candidate"] is False
        assert watch_item["is_entry_candidate"] is False
        assert "code" in watch_item
        assert "company_name" in watch_item


def test_get_today_watchlist_runs_with_ma_order_module():
    # 並び順ウォッチ（entry_signal_spec.md 15章）: "ma_order"のみを選択しても、
    # ma_order自体が監視銘柄候補を出せる
    stocks = get_active_stocks().head(3)

    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["ma_order"], ma_mode="full",
    )

    assert isinstance(watchlist, list)

    for watch_item in watchlist:
        assert watch_item["is_order_watch_candidate"] is True
        assert watch_item["is_watch_candidate"] is False
        assert watch_item["is_cross_watch_candidate"] is False
        assert watch_item["is_entry_candidate"] is False
        assert "code" in watch_item
        assert "company_name" in watch_item


def test_is_merged_watch_candidate_single_module_matches_that_flag():
    result = {
        "is_watch_candidate": True,
        "is_cross_watch_candidate": False,
        "is_order_watch_candidate": False,
    }

    assert _is_merged_watch_candidate(result, ["bounce"]) is True
    assert _is_merged_watch_candidate(result, ["ma_cross_watch"]) is False
    assert _is_merged_watch_candidate(result, ["ma_order"]) is False


def test_is_merged_watch_candidate_requires_all_selected_modules():
    # 2つ選択している場合、片方だけTrueではFalse（AND結合）
    partial = {
        "is_watch_candidate": True,
        "is_cross_watch_candidate": False,
        "is_order_watch_candidate": False,
    }
    both = {
        "is_watch_candidate": True,
        "is_cross_watch_candidate": True,
        "is_order_watch_candidate": False,
    }

    assert _is_merged_watch_candidate(partial, ["bounce", "ma_cross_watch"]) is False
    assert _is_merged_watch_candidate(both, ["bounce", "ma_cross_watch"]) is True


def test_is_merged_watch_candidate_false_when_no_watch_module_selected():
    # 監視系モジュール（bounce・ma_cross_watch・ma_order）を1つも選択していない
    # 場合は、全部Trueが渡されても常にFalse（候補一覧と違い無条件Trueにはしない）
    result = {
        "is_watch_candidate": True,
        "is_cross_watch_candidate": True,
        "is_order_watch_candidate": True,
    }

    assert _is_merged_watch_candidate(result, ["perfect_golden_cross"]) is False
    assert _is_merged_watch_candidate(result, []) is False


def test_get_today_watchlist_merges_bounce_cross_watch_and_order_watch_modules():
    # 反発・MA60/100接近ウォッチ・並び順ウォッチを同時選択した場合、1つの
    # watchlistにまとめて含まれるが、選択したものをすべて満たす銘柄だけに
    # 絞り込まれる（AND結合、2026-08-23改訂。以前はいずれか1つでも該当すれば
    # 含めるOR結合だった）
    stocks = get_active_stocks().head(300)

    watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=["ma_order", "bounce", "ma_cross_watch"],
    )

    assert isinstance(watchlist, list)

    for watch_item in watchlist:
        assert watch_item["is_watch_candidate"] is True
        assert watch_item["is_cross_watch_candidate"] is True
        assert watch_item["is_order_watch_candidate"] is True
        assert watch_item["is_entry_candidate"] is False


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


def test_get_today_scan_results_flags_watchlist_codes_in_candidates():
    # 候補一覧は既に監視銘柄として登録済みの銘柄を除外しない（2026-08-23改訂。
    # 以前は除外していたが、「候補一覧も監視銘柄登録済みの銘柄を表示してほしい」
    # との要望を受けて変更した）。is_already_watchlisted=Trueで区別できる
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

        matching = [c for c in result["candidates"] if c["code"] == code]
        assert len(matching) == 1
        assert matching[0]["is_already_watchlisted"] is True
    finally:
        delete_watchlist_stocks_by_code(code)


def test_get_today_scan_results_excludes_open_trade_codes_from_watchlist(monkeypatch):
    create_trades_table()

    stocks = get_active_stocks().head(3)
    code = stocks.iloc[0]["code"]
    company_name = stocks.iloc[0]["company_name"]

    add_trade(
        code=code, company_name=company_name, direction="long", timeframe="daily",
        trade_date="2000-01-01", entry_price=100.0, exit_price=None, quantity=100,
    )

    def fake_evaluate_stock(code, direction, timeframe, min_history, modules,
                             ma_mode, min_volume, min_price, max_price):
        return {"is_entry_candidate": False, "is_watch_candidate": True}

    monkeypatch.setattr("service.screening_service._evaluate_stock", fake_evaluate_stock)

    try:
        # modulesは"bounce"のみ（fake_evaluate_stockが返すis_watch_candidateに
        # 対応するモジュールだけ）にする。"ma_order"も含めると、AND結合
        # （_is_merged_watch_candidate）でis_order_watch_candidateも要求され、
        # fakeの戻り値には無いため、除外ロジックを検証する前に候補から
        # 外れてしまう
        result = get_today_scan_results(
            direction="long", stocks=stocks, modules=["bounce"],
            min_market_cap=0,
        )

        assert code not in [w["code"] for w in result["watchlist"]]
    finally:
        for trade in get_all_trades():
            if trade["code"] == code and trade["trade_date"] == "2000-01-01":
                delete_trade(trade["id"])


def test_get_today_scan_results_includes_watchlist_codes_in_watchlist_flagged(monkeypatch):
    # 候補一覧と異なり、監視銘柄候補一覧は既に監視銘柄として登録済みの銘柄を
    # 除外しない（2026-08-23改訂）。代わりにis_already_watchlisted=Trueを
    # 立てて、呼び出し側（UI）でグレー表示・選択不可にできるようにする
    create_watchlist_table()

    stocks = get_active_stocks().head(3)
    code = stocks.iloc[0]["code"]
    company_name = stocks.iloc[0]["company_name"]

    add_watchlist_stock(
        code=code, company_name=company_name, direction="long", timeframe="daily",
        added_date="2000-01-01",
    )

    def fake_evaluate_stock(code, direction, timeframe, min_history, modules,
                             ma_mode, min_volume, min_price, max_price):
        return {"is_entry_candidate": False, "is_watch_candidate": True}

    monkeypatch.setattr("service.screening_service._evaluate_stock", fake_evaluate_stock)

    try:
        result = get_today_scan_results(
            direction="long", stocks=stocks, modules=["bounce"],
            min_market_cap=0,
        )

        matching = [w for w in result["watchlist"] if w["code"] == code]
        assert len(matching) == 1
        assert matching[0]["is_already_watchlisted"] is True
    finally:
        delete_watchlist_stocks_by_code(code)


def test_get_today_scan_results_watchlist_flags_other_codes_as_not_already_watchlisted(monkeypatch):
    create_watchlist_table()

    stocks = get_active_stocks().head(3)

    def fake_evaluate_stock(code, direction, timeframe, min_history, modules,
                            ma_mode, min_volume, min_price, max_price):
        return {"is_entry_candidate": False, "is_watch_candidate": True}

    monkeypatch.setattr("service.screening_service._evaluate_stock", fake_evaluate_stock)

    result = get_today_scan_results(
        direction="long", stocks=stocks, modules=["bounce"], min_market_cap=0,
    )

    assert len(result["watchlist"]) == len(stocks)
    assert all(w["is_already_watchlisted"] is False for w in result["watchlist"])


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
    modules = ["ma_order", "bounce", "ma_cross_watch"]

    result = get_today_scan_results(
        direction="long", stocks=stocks, modules=modules, min_market_cap=0,
    )

    assert set(result.keys()) == {"candidates", "watchlist"}

    expected_candidates = get_today_candidates(
        direction="long", stocks=stocks, modules=modules, min_market_cap=0,
    )
    expected_watchlist = get_today_watchlist(
        direction="long", stocks=stocks, modules=modules,
    )

    assert [c["code"] for c in result["candidates"]] == [c["code"] for c in expected_candidates]
    assert (
        sorted(w["code"] for w in result["watchlist"])
        == sorted(w["code"] for w in expected_watchlist)
    )
    assert all(c["is_entry_candidate"] for c in result["candidates"])
    # modulesが3つとも選択されているため、watchlistの各要素は3つすべてを
    # 満たしている（AND結合、2026-08-23改訂）
    assert all(
        w["is_watch_candidate"] and w["is_cross_watch_candidate"] and w["is_order_watch_candidate"]
        for w in result["watchlist"]
    )


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
