import pandas as pd

from config.config import LARGE_CAP_MARKET_CAP_THRESHOLD
from database.stock_master_reader import get_active_stocks
from service.screening_service import (
    evaluate_single_stock,
    format_reason,
    get_large_cap_stocks,
    get_prime_stocks,
    get_stock_chart_data,
    get_today_candidates,
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


def test_evaluate_single_stock_returns_error_for_unknown_code():
    result = evaluate_single_stock("0000")

    assert result["code"] == "0000"
    assert "error" in result


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
                   "sma5", "sma20", "sma60"]:
        assert column in df.columns

    assert list(df["date"]) == sorted(df["date"])


def test_get_stock_chart_data_weekly_has_fewer_rows_than_daily():
    code = get_active_stocks().iloc[0]["code"]

    daily = get_stock_chart_data(code, timeframe="daily")
    weekly = get_stock_chart_data(code, timeframe="weekly")

    assert len(weekly) < len(daily)


def test_format_reason_pattern_a():
    candidate = {"pattern": "A", "bounce_number": 1}

    assert format_reason(candidate) == "支持線/抵抗線付近の半分シグナル（反発1回目）"


def test_format_reason_pattern_b_long():
    candidate = {"pattern": "B", "bounce_number": 2, "direction": "long"}

    assert format_reason(candidate) == "5日線・20日線ゴールデンクロスの半分シグナル（反発2回目）"


def test_format_reason_pattern_b_short():
    candidate = {"pattern": "B", "bounce_number": 1, "direction": "short"}

    assert format_reason(candidate) == "5日線・20日線デッドクロスの半分シグナル（反発1回目）"
